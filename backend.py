
import json
from oauth2client.service_account import ServiceAccountCredentials
from requests import request
import sqlite3

import google.oauth2
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery #type:ignore
import google
import google.auth.transport.requests
import gspread

discordHeaders = {
	"Content-Type": "application/json",
	"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"
}

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

# ! Remove in production
def uploadTestDataUsersDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	sheet_id = "1iz9IkmMlmFr3Zykjrqot0Y_0PQsQw3ZWZR7JZ4YFkH0"
	whatsapp_key = "EAAP4SJAmuEwBOZC4vEsZA6nkb5lbTrZCRv3ukKrO5S8oE2GMIOMVfL29PHzQBzQBbdTK9nafmzNMm3mKkQ1XxS1rGKHIjXZATG7vqjFoAomZCdPmZCW0UOGCZBTkfQkMpomHAMt6cDfEhbKV4JooZAryKOPd2iRwgWwlZCLWYxtDYxoIxZAHR7Sx51VrIp4OTQQwTgZAgZDZD"
	whatsapp_id = "469064916301145"
	last_row = 1
	cursor.execute("INSERT INTO users (sheet_id, whatsapp_key, last_row, whatsapp_id) values (?,?,?,?)", (sheet_id, whatsapp_key, last_row, whatsapp_id))

	user_id = 1
	message_id = "wamid.HBgLNDA3MjE3NTI4NzYVAgARGBJENTBCNkM1OTM4QUQzOEFGQ0YA"
	event_type = 'sent'
	cursor.execute("INSERT INTO message_events (user_id, message_id, event_type) values (?,?,?)", (user_id, message_id, event_type))
	conn.commit()
	
	print("inserted testing data in DB")

def initializeUserDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	# ==== Initiialize users table with | user_id as key | sheet_id | whatsapp_key | whatsapp_id |last_row ====
	# whatsapp_key = authorization token
	# whatsapp_id = phone number id
	cursor.execute("""
				CREATE TABLE IF NOT EXISTS users (
				user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				sheet_id TEXT NOT NULL UNIQUE,
				whatsapp_key TEXT NOT NULL UNIQUE,
				whatsapp_id TEXT NOT NULL,
				last_row INTEGER NOT NULL
				);
	""")
	conn.commit()

def initializaEventsDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	# ==== Initiialize users table with | user_id as key | sheet_id | whatsapp_key | last_row ====
	cursor.execute("""
				CREATE TABLE IF NOT EXISTS message_events (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				user_id INTEGER NOT NULL,
				message_id TEXT NOT NULL UNIQUE,
				timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
				event_type TEXT CHECK(event_type IN ('sent', 'seen', 'responded')) NOT NULL,
				FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
				);
	""")
	conn.commit()

class user:
	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

	def __init__(self, user_id):
		self.user_id = user_id
		
		current_user = self.get_user_data()
		# print(current_user, type(current_user))

		if current_user !=None:
			# * Get all data based on user_id
			self.sheet_id = current_user[0]
			self.whatsapp_token = current_user[1]
			self.whatsapp_id = current_user[2]
			self.last_row = current_user[3] 
			self.url = f"https://graph.facebook.com/v21.0/{self.whatsapp_id}/messages"
			template_file_name = f"{self.user_id}.json"
			self.message_template = self.load_json(filename=template_file_name)
			headers["Authorization"] = "Bearer " + self.whatsapp_token

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

	def get_user_data(self):
		# TODO: Convert to fetchall() method to check for any duplicates
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE user_id = ?" , (self.user_id,))
			return cursor.fetchone()

	def update_messages_table(self, message_id,event_type):
		with sqlite3("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO message_events (user_id, message_id, event_type) VALUES (?,?,?)
			""", (self.user_id, message_id, event_type))
			conn.commit()

	# !! Figure it out shithead
	# creds = ServiceAccountCredentials.from_json_keyfile_dict(self.sheet_creds, scope)
	# client = gspread.authorize(creds)
	# sheet = client.open_by_key(self.sheet_id)

	creds = google.oauth2.credentials.Credentials()

	def updateLastLine(last_row, self):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE users SET last_row = ? WHERE user_id = ?", (last_row, self.user_id))
			conn.commit()

	def listener(self):
		# * Bafta coaie
		# !! This function is critical
		# TODO: Based on the last row inside the db for the respective user.
		# TODO: Check if there is a difference between the no of lines inside gSheet and in DB
		nameCol = sheet.get(f'B{self.last_row}:B')

		# * When the row is empty, length of nameCol is 1 and len of nameCol[0] is 0
		print("Waiting...")
		if(len(nameCol) >=1 and len(nameCol[0]) != 0):
			print("nameCol : ", nameCol) 
			# print("Length : ", len(nameCol))
			# print('nameCol[0] : ', nameCol[0])
			# print('Length nameCol[0] : ', len(nameCol[0]))
			self.sender()
			# print("-----------------")
	
	def sender(self):
		name_col = sheet.get(f'C{self.last_row}:C')
		phoneNr_col = sheet.get(f'D{self.last_row}:D', value_render_option='FORMULA')

		print(phoneNr_col)

		for i in range(len(name_col)): # Go through every user and send them a custom message
			print("index : ", i)
			self.message_template['to'] = '40' + transformPhoneNumber(phoneNr_col[i][0])
			self.message_template['template']['components'][0]['parameters'][0]['text'] = name_col[i][0]
			# print(f"{template['to']} -> {template['template']['components'][0]['parameters'][0]['text']}") # Actual live data taken from sheets
			response = request("POST", self.url, data=json.dumps(self.message_template), headers=headers)

			if(response.status_code == 200):
				print(f"[{response.status_code}] Sent {name_col[i][0]} : 40{phoneNr_col[i][0]} template message named - {self.message_template['template']['name']}")
			else:
				print(f"[{response.status_code}] {response.text}")

			print(response.text)
			print(response.status_code)
		new_last_line = self.last_row + len(name_col)
		self.updateLastLine(new_last_line)

if __name__ == "__main__":
	vlad = user(1)
	# initializaEventsDB()
	# initializeUserDB()
	# uploadTestDataUsersDB()
