
import json
from requests import request
import sqlite3

import google.oauth2
import google.oauth2.credentials
from google.auth.transport.requests import Request
import googleapiclient.discovery
import google
import google.auth.transport.requests
import gspread
import threading

from datetime import datetime
from time import sleep

headers = {
	"Content-Type" : "application/json",
	"Authorization" : None
}

def getCurrentTime():
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	return now

def transformPhoneNumber(phoneNr):
	phoneNr = str(phoneNr)
	if(phoneNr[0] == '7'): return phoneNr
	phoneNumber = phoneNr
	phoneNumber = phoneNr[4:7]+phoneNr[8:11]+phoneNr[12:15]
	return phoneNumber

def createAccount(sheet_id: str, whatsapp_key: str, whatsapp_id:str, email: str, price_lead:int, template_name: str, column_name:str, column_phone:str ) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor .execute("INSERT INTO users (sheet_id, whatsapp_key, whatsapp_id, email, last_row, price_lead, template_name, column_name, column_phone) VALUES (?,?,?,?,1,?,?,?,?)",
		(sheet_id, whatsapp_key, whatsapp_id, email, price_lead))
		conn.commit()
		return True

class User:
	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

	# TODO: After modifying the database, change the constructor to read new data
	# TODO: Implement a caching system for user data to avoid multiple DB calls
	def __init__(self, user_id:int):
		self.user_id = user_id
		self.thread = None
		current_user = self.get_user_data()

		if current_user != None:
			# * Get all data based on user_id
			self.sheet_id = current_user[1]
			self.whatsapp_token = current_user[2]
			self.whatsapp_id = current_user[3]
			self.email = current_user[4]
			self.last_row = current_user[6] 
			self.template_name = current_user[8]
			self.name_col = current_user[9]
			self.phone_col = current_user[10]

			message_limit = self.get_message_limit()
			self.message_limit_enabled = message_limit[1]
			self.message_limit_value = message_limit[2]

			self.url = f"https://graph.facebook.com/v21.0/{self.whatsapp_id}/messages"
			
			# TODO: check if the filename is correct | file is in folder

			template_file_name = "template.json"
			self.message_template = self.load_json(filename=template_file_name)
			self.message_template['template']['name'] = self.template_name
			headers["Authorization"] = "Bearer " + self.whatsapp_token

			self.is_running = self.get_script_status()

		else:
			raise ValueError(f"No user has been found with ID = {self.user_id}. Check if data is correct or check DB!")
	
	def load_json(self, filename):
		# print(f"[{getCurrentTime()}]OPEN FILE: {filename}")
		try:
			with open(f"message_templates/{filename}", "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			print(f"[{getCurrentTime()}] Error: File not found")
			return None
		except json.JSONDecodeError:
			print(f"[{getCurrentTime()}] Error: Invalid Json Format")
			return None

	def save_credentials_to_db(self, user_id : int, credentials : dict):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				UPDATE users SET credentials_json = ? WHERE user_id = ?;
			""", (credentials.to_json(), user_id))
			conn.commit()

	def load_credentials_from_db(self,user_id : int):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT credentials_json FROM users WHERE user_id = ?", (user_id, ))
			row = cursor.fetchone()
			if row[0] is not None:
				return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
			return None

	def refresh_credentials(self, user_id: int):
		try:
			creds = self.load_credentials_from_db(user_id)
			if not creds:
				raise Exception(f"No google credentials found for user: {user_id}")
			if creds.expired and creds.refresh_token:
				creds.refresh(Request())
				self.save_credentials_to_db(user_id, creds)
				
			return creds
		except Exception as e:
			print(f"[{getCurrentTime()}][User {self.user_id}] refresh-credentials -> ERROR: {e}")
	
	def get_user_data(self):
		try:
			with sqlite3.connect("database.db") as conn:
				cursor = conn.cursor()
				cursor.execute("SELECT * FROM users WHERE user_id = ?" , (self.user_id,))
				result =  cursor.fetchall()

				if len(result) > 1:
					print(f"[{getCurrentTime()}][User {self.user_id}] ERROR!!! - More than one user found with ID: {self.user_id}. Please check database for duplicates!")
				
				return result[0] if result else None
		except json.JSONDecodeError:
			print(f"[{getCurrentTime()}][User {self.user_id}] Error decoding JSON data for user {self.user_id}")
			return None

	def get_message_limit(self):
		try:
			with sqlite3.connect("database.db") as conn:
				cursor = conn.cursor()
				cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (self.user_id,))
				result = cursor.fetchall()

				if len(result) > 1:
					print(f"[{getCurrentTime()}][User {self.user_id}] ERROR!!!! - More than one user found with ID: {self.user_id}. Please check database for duplicates!")
					return result[0] if result else None
				
				if len(result) == 0:
					cursor.execute("INSERT INTO message_limit (user_id, is_on, limit_value) VALUES (?,?,?)", (self.user_id, 0, 100))
					conn.commit()
					cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (self.user_id,))
					result = cursor.fetchall()
					return result[0] if result else None
				
				return result[0] if result else None
		
		except json.JSONDecodeError:
			print(f"[{getCurrentTime()}][User {self.user_id}] Error decoding JSON data for user {self.user_id}")
			return None

	def reset_message_limit(self, date_now: str):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE message_limit SET current_value = 0, last_day = ? WHERE user_id = ?", (date_now, self.user_id))
			conn.commit()
		print(f"[{getCurrentTime()}][User {self.user_id}] Message limit reset for date: {date_now}")

	def update_message_current_count(self):
		try:
			with sqlite3.connect("database.db") as conn:
				cursor = conn.cursor()
				cursor.execute("""
				UPDATE message_limit SET current_count = current_count + 1 WHERE user_id = ?;
				""", (self.user_id,))
				conn.commit()
				return True
		except sqlite3.Error as e:
			print(f"[{getCurrentTime()}][User {self.user_id}] Error updating message count: {e}")
			return False

	def update_message_limits(self, is_on: bool, value: int):
		try:
			with sqlite3.connect("database.db") as conn:
				cursor = conn.cursor()
				cursor.execute("""
				INSERT INTO message_limit (user_id, is_on, limit_value)
				VALUES (?, ?, ?)
				ON CONFLICT(user_id) DO UPDATE SET
					is_on = excluded.is_on,
					limit_value = excluded.limit_value;
				""", (self.user_id, is_on, value))
				conn.commit()
				return True

		except sqlite3.Error as e:
			print(f"[{getCurrentTime()}][User {self.user_id}] Error updating message limits: {e}")
			return False

	def update_messages_table(self, message_id, conversation_id, event_type):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO message_events (user_id, message_id, event_type) VALUES (?,?,?,?)
			""", (self.user_id, message_id, event_type))
			conn.commit()

	def update_account_details(self, email: str, wNumber: str, wToken: str, gSheetID: str, price_lead: int, template_name: str, name_col: str, phone_col: str) -> bool:
		name_col = name_col.upper()
		phone_col = phone_col.upper()

		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE users SET email = ?, whatsapp_key = ?, whatsapp_id = ?, sheet_id = ?, price_lead = ?, template_name = ?, column_name = ?, column_phone = ? WHERE user_id = ?", (email, wToken, wNumber, gSheetID, price_lead, template_name,name_col, phone_col, self.user_id))
			conn.commit()
		return True

	def update_last_line(self, last_row):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE users SET last_row = ? WHERE user_id = ?", (last_row, self.user_id))
			conn.commit()

	def get_script_status(self) -> bool:
		with sqlite3.connect('database.db') as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT status FROM script_status WHERE user_id = ?", (self.user_id,))
			result = cursor.fetchone()
			if result:
				status = result[0]
				if status == 'running': return True
				elif status == 'stopped': return False
			else:
				cursor.execute("INSERT INTO script_status (user_id, status) VALUES (?, ?)", (self.user_id, "stopped"))
				conn.commit()
				return False
			
			raise ValueError(f"Either no value was found for USER_ID: {self.user_id} OR bad value from status_script: {result}")

	def getPriceLead(self) -> int:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT price_lead FROM users WHERE user_id = ?", (self.user_id,))
			result = cursor.fetchone()[0]
			return result

	def update_script_status(self, status):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO script_status (user_id, status) VALUES (?,?) ON CONFLICT (user_id) DO UPDATE SET status = excluded.status
			""", (self.user_id, status))
			conn.commit()

	def launch_listener(self):
		if self.is_running:
			print(f"[User {self.user_id}] Script is already running")
			return

		self.thread = threading.Thread(target=self.listener, daemon=True)
		self.thread.start()

		self.is_running = True
		self.update_script_status("running")
		
		print(f"[{getCurrentTime()}][User {self.user_id}] {self.thread.name} started")
		print(f"[{getCurrentTime()}][User {self.user_id}] Started script")

	def stop_listener(self):
		print(f"[{getCurrentTime()}][User {self.user_id}] {self.thread}")
		# TODO: Fix error where script is already stopped
		if not self.is_running:
			print(f"[{getCurrentTime()}][User {self.user_id}] Script is already stopped")
			return None

		self.is_running = False
		self.update_script_status("stopped")
		self.thread.join()

		print(f"[{getCurrentTime()}][User {self.user_id}] Script stopped")

	def messageLimit(self):
		result = get_message_limit()
		date_now = datetime.now().strftime("%Y-%m-%d")
		
		if result[1] == 0:
			return True

		elif result[4] != date_now:
			reset_message_limit(self, date_now)
			return True

		elif result[4] == date_now and result[3] < result[2]:
			return True
		
		return False

	def listener(self):
		try:
			creds = self.refresh_credentials(self.user_id)
			if not creds:
				print(f"[{getCurrentTime()}][User {self.user_id}] !!!!No creds found!!!!")
				return None

			client = gspread.authorize(creds)
			self.sheet = client.open_by_key(self.sheet_id).sheet1

			while self.is_running:
				try:
					sheet_range = f"{self.name_col}{self.last_row}:{self.name_col}"
					# print("--%s--" %sheet_range)
					name_column = self.sheet.get(sheet_range)

					# * When the row is empty, length of nameCol is 1 and len of nameCol[0] is 0
					print(f"[{getCurrentTime()}][User {self.user_id}] Waiting...")
					if(len(name_column) >=1 and len(name_column[0]) != 0):
						print("nameCol : ", name_column) 
						self.sender()
						# print("Length : ", len(nameCol))
						# print('nameCol[0] : ', nameCol[0])
						# print('Length nameCol[0] : ', len(nameCol[0]))
						# print("-----------------")
					creds = self.refresh_credentials(self.user_id)
				except Exception as e:
					print(f"[{getCurrentTime()}][User {self.user_id}] !-! Error: {e}")
					sleep(30)
				
				sleep(10)
		except Exception as e:
			print(f"[{getCurrentTime()}][User {self.user_id}] !!! Failed to start: {e}")
	
	def sender(self):
		if messageLimit() == False:
			print(f"[{getCurrentTime()}] Message limit reached: {count} messages sent today.")
			self.stop_listener()
			return None

		creds = self.refresh_credentials(self.user_id)

		client = gspread.authorize(creds)
		self.sheet = client.open_by_key(self.sheet_id).sheet1

		name_col = self.sheet.get(f'{self.name_col}{self.last_row}:{self.name_col}')
		if(len(name_col) >=1 and len(name_col[0]) != 0):
			phoneNr_col = self.sheet.get(f'{self.phone_col}{self.last_row}:{self.phone_col}', value_render_option='FORMULA')

			for i in range(len(name_col)): # Go through every user and send them a custom message
				print("index : ", i)
				self.message_template['to'] = '40' + transformPhoneNumber(phoneNr_col[i][0])
				self.message_template['template']['components'][0]['parameters'][0]['text'] = name_col[i][0]
				response = request("POST", self.url, data=json.dumps(self.message_template), headers=headers)

				if(response.status_code == 200):
					response_json = json.loads(response.text)
					message_id = response_json['messages'][0]['id']
					conversation_id = 'none'

					self.update_messages_table(str(message_id),str(conversation_id),'sent')
					print(f"[{getCurrentTime()}][User {self.user_id}][{response.status_code}] Sent {name_col[i][0]} : 40{phoneNr_col[i][0]} template message named - {self.message_template['template']['name']}")
				else:
					print(f"[{getCurrentTime()}][User {self.user_id}][{response.status_code}] {response.text}")

				print(response.status_code)
			new_last_line = self.last_row + len(name_col)
			self.last_row = new_last_line
			self.update_last_line(new_last_line)