
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

class User:
	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

	def __init__(self, user_id:int):
		self.user_id = user_id
		self.session_credentials = self.refresh_credentials(user_id)

		current_user = self.get_user_data()
		# print(current_user, type(current_user))

		if current_user !=None:
			# * Get all data based on user_id
			self.sheet_id = current_user[1]
			self.whatsapp_token = current_user[2]
			self.whatsapp_id = current_user[3]
			self.email = current_user[4]
			self.last_row = current_user[5] 
			self.url = f"https://graph.facebook.com/v21.0/{self.whatsapp_id}/messages"
			template_file_name = f"{self.user_id}.json"
			self.message_template = self.load_json(filename=template_file_name)
			headers["Authorization"] = "Bearer " + self.whatsapp_token

			client = gspread.authorize(self.session_credentials)
			self.sheet = client.open_by_key(self.sheet_id).sheet1

			self.is_running = self.get_script_status()

		else:
			raise ValueError(f"No user has been found with ID = {self.user_id}. Check if data is correct or check DB!")
	
	def load_json(self, filename):
		print(f"OPEN FILE: {filename}")
		try:
			with open(f"message_templates/{filename}", "r", encoding="utf-8") as file:
				return json.load(file)
		except FileNotFoundError:
			print("Error: File not found")
			return None
		except json.JSONDecodeError:
			print("Error: Invalid Json Format")
			return None

	def save_credentials_to_db(user_id : int, credentials : dict):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				UPDATE users SET credentials_json = ? WHERE user_id = ?;
			""", (credentials.to_json(), user_id))
			conn.commit()

	def load_credentials_from_db(user_id : int):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT credentials_json FROM users WHERE user_id = ?", (user_id, ))
			row = cursor.fetchone()
			if row:
				return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
			return None

	def refresh_credentials(self, user_id: int) :
		creds = self.load_credentials_from_db(user_id)
		if not creds:
			raise Exception(f"No credentials found for user: {user_id}")
		
		if creds.expired and creds.refresh_token:
			creds.refresh(Request())
			self.save_credentials_to_db(user_id, creds)
			
		return creds
	
	def get_user_data(self):
		# TODO: Convert to fetchall() method to check for any duplicates
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE user_id = ?" , (self.user_id,))
			return cursor.fetchone()

	def update_messages_table(self, message_id,event_type):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO message_events (user_id, message_id, event_type) VALUES (?,?,?)
			""", (self.user_id, message_id, event_type))
			conn.commit()

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
			
			raise ValueError(f"Either no value was found for USER_ID: {self.user_id} OR bad value from status_script: {result}")

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

	def stop_listener(self):
		if not self.is_running:
			print(f"[User {self.user_id}] Script is already stopped")
			return
		self.is_running = False
		self.update_script_status("stopped")

	def listener(self):
		# TODO: Check if there is a difference between the no of lines inside gSheet and in DB
		name_col = self.sheet.get(f'B{self.last_row}:B')

		# * When the row is empty, length of nameCol is 1 and len of nameCol[0] is 0
		print("Waiting...")
		if(len(name_col) >=1 and len(name_col[0]) != 0):
			print("nameCol : ", name_col) 
			self.sender()
			# print("Length : ", len(nameCol))
			# print('nameCol[0] : ', nameCol[0])
			# print('Length nameCol[0] : ', len(nameCol[0]))
			# print("-----------------")
		sleep(5)
	
	def sender(self):
		name_col = self.sheet.get(f'C{self.last_row}:C')
		if(len(name_col) >=1 and len(name_col[0]) != 0):
			print("nameCol : ", name_col) 
			phoneNr_col = self.sheet.get(f'D{self.last_row}:D', value_render_option='FORMULA')

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

					print(message_id)
					self.update_messages_table(str(message_id),'sent')
					print(f"[{response.status_code}] Sent {name_col[i][0]} : 40{phoneNr_col[i][0]} template message named - {self.message_template['template']['name']}")
				else:
					print(f"[{response.status_code}] {response.text}")

				# print(response.text)
				print(response.status_code)
			new_last_line = self.last_row + len(name_col)
			self.update_last_line(new_last_line)

