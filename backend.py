
import json
# from oauth2client.service_account import ServiceAccountCredentials
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

def transformPhoneNumber(phoneNr):
	phoneNr = str(phoneNr)
	if(phoneNr[0] == '7'): return phoneNr
	phoneNumber = phoneNr
	phoneNumber = phoneNr[4:7]+phoneNr[8:11]+phoneNr[12:15]
	return phoneNumber

def createAccount(sheet_id: str, whatsapp_key: str, whatsapp_id:str, email: str, price_lead) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor .execute("INSERT INTO users (sheet_id, whatsapp_key, whatsapp_id, email, last_row, price_lead) VALUES (?,?,?,?,1,?)",
		(sheet_id, whatsapp_key, whatsapp_id, email, price_lead))
		conn.commit()
		return True

class User:
	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

	def __init__(self, user_id:int):
		# TODO: Set these variables to be edited in profile page
		self.name_col = 'C'
		self.phone_col = 'D'

		self.user_id = user_id

		self.thread = None


		current_user = self.get_user_data()
		# print(current_user, type(current_user))

		if current_user !=None:
			# * Get all data based on user_id
			self.sheet_id = current_user[1]
			self.whatsapp_token = current_user[2]
			self.whatsapp_id = current_user[3]
			self.email = current_user[4]
			self.last_row = current_user[6] 
			self.url = f"https://graph.facebook.com/v21.0/{self.whatsapp_id}/messages"
			template_file_name = "template.json"
			self.message_template = self.load_json(filename=template_file_name)
			headers["Authorization"] = "Bearer " + self.whatsapp_token

			self.is_running = self.get_script_status()

		else:
			raise ValueError(f"No user has been found with ID = {self.user_id}. Check if data is correct or check DB!")
	
	def load_json(self, filename):
		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		# print(f"[{now}]OPEN FILE: {filename}")
		try:
			with open(f"message_templates/{filename}", "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			print(f"[{now}] Error: File not found")
			return None
		except json.JSONDecodeError:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			print(f"[{now}] Error: Invalid Json Format")
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
			if row:
				return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
			return None

	def refresh_credentials(self, user_id: int):
		try:
			creds = self.load_credentials_from_db(user_id)
			if not creds:
				raise Exception(f"No credentials found for user: {user_id}")
			
			if creds.expired and creds.refresh_token:
				creds.refresh(Request())
				self.save_credentials_to_db(user_id, creds)
				
			return creds
		except Exception as e:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			print(f"[{now}][User {self.user_id}] refresh-credentials -> ERROR: {e}")
	
	def get_user_data(self):
		# TODO: Convert to fetchall() method to check for any duplicates
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE user_id = ?" , (self.user_id,))
			return cursor.fetchone()

	def update_messages_table(self, message_id, conversation_id, event_type):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO message_events (user_id, message_id,conversation_id, event_type) VALUES (?,?,?,?)
			""", (self.user_id, message_id, conversation_id, event_type))
			conn.commit()

	def update_account_details(self, email: str, wNumber: str, wToken: str, gSheetID: str, price_lead) -> bool:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE users SET email = ?, whatsapp_key = ?, whatsapp_id = ?, sheet_id = ?, price_lead = ? WHERE user_id = ?", (email, wToken, wNumber, gSheetID, price_lead, self.user_id))
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
		self.is_running = True
		self.update_script_status("running")
		self.thread = threading.Thread(target=self.listener, daemon=True)
		self.thread.start()
		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		print(f"[{now}][User {self.user_id}] Script started!!!")

	def stop_listener(self):
		if not self.is_running:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			print(f"[{now}][User {self.user_id}] Script is already stopped")
			return
		self.is_running = False
		self.update_script_status("stopped")
		self.thread.join()

		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		print(f"[{now}][User {self.user_id}] Script stopped")

	def listener(self):
		try:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")

			creds = self.refresh_credentials(self.user_id)
			if not creds:
				now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
				print(f"[{now}][User {self.user_id}] !!!!No creds found!!!!")
				return
			
			# try:	
			# * Works
			client = gspread.authorize(creds)
			self.sheet = client.open_by_key(self.sheet_id).sheet1
			# except Exception as e:
			# 	print(f"[{now}][User {self.user_id}] Gspread auth error 2: {e}")

			while self.is_running:
				try:
					now = datetime.now().strftime("%y-%m-%d %H:%M:%S")

					sheet_range = f"{self.name_col}{self.last_row}:{self.name_col}"
					# print("--%s--" %sheet_range)
					name_column = self.sheet.get(sheet_range)

					# * When the row is empty, length of nameCol is 1 and len of nameCol[0] is 0
					print(f"[{now}][User {self.user_id}] Waiting...")
					if(len(name_column) >=1 and len(name_column[0]) != 0):
						print("nameCol : ", name_column) 
						self.sender()
						# print("Length : ", len(nameCol))
						# print('nameCol[0] : ', nameCol[0])
						# print('Length nameCol[0] : ', len(nameCol[0]))
						# print("-----------------")
					creds = self.refresh_credentials(self.user_id)
				except Exception as e:
					now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
					print(f"[{now}][User {self.user_id}] !-! Error: {e}")
					sleep(30)
				
				sleep(5)
		except Exception as e:
			now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			print(f"[{now}][User {self.user_id}] !!! Failed to start: {e}")
	
	def sender(self):
		creds = self.refresh_credentials(self.user_id)

		client = gspread.authorize(creds)
		self.sheet = client.open_by_key(self.sheet_id).sheet1

		name_col = self.sheet.get(f'{self.name_col}{self.last_row}:{self.name_col}')
		if(len(name_col) >=1 and len(name_col[0]) != 0):
			# print("nameCol : ", name_col) 
			phoneNr_col = self.sheet.get(f'{self.phone_col}{self.last_row}:{self.phone_col}', value_render_option='FORMULA')

			print(phoneNr_col)

			for i in range(len(name_col)): # Go through every user and send them a custom message
				print("index : ", i)
				self.message_template['to'] = '40' + transformPhoneNumber(phoneNr_col[i][0])
				self.message_template['template']['components'][0]['parameters'][0]['text'] = name_col[i][0]
				# print(f"{template['to']} -> {template['template']['components'][0]['parameters'][0]['text']}") # Actual live data taken from sheets
				response = request("POST", self.url, data=json.dumps(self.message_template), headers=headers)

				if(response.status_code == 200):
					# print(response.text, type(response.text))
					response_json = json.loads(response.text)
					message_id = response_json['messages'][0]['id']
					conversation_id = 'none'

					print(message_id)
					self.update_messages_table(str(message_id),str(conversation_id),'sent')
					now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
					print(f"[{now}][User {self.user_id}][{response.status_code}] Sent {name_col[i][0]} : 40{phoneNr_col[i][0]} template message named - {self.message_template['template']['name']}")
				else:
					now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
					print(f"[{now}][User {self.user_id}][{response.status_code}] {response.text}")

				# print(response.text)
				print(response.status_code)
			new_last_line = self.last_row + len(name_col)
			self.last_row = new_last_line
			self.update_last_line(new_last_line)

