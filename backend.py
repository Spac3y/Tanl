
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sqlite3
import json

# TODO: Get these variables from sql db:
# ?? | meta_id | 

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

def initializeUserDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	# ==== Initiialize users table with | user_id as key | sheet_id | whatsapp_key | whatsapp_id |last_row ====
	# whatsapp_key = authorization token
	# whatsapp_id = phone number id
	cursor.execute("""
				CREATE TABLE IF NOT EXISTS users (
				user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				sheet_id TEXT NOT NULL,
				whatsapp_key TEXT NOT NULL,
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
				message_id TEXT NOT NULL,
				timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
				event_type TEXT CHECK(event_type IN ('sent', 'seen', 'responded')) NOT NULL,
				FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
				);
	""")
	conn.commit()

class user:
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
	
	def __init__(self, user_id):
		self.user_id = user_id
	
		headers["Authorization"] = "Bearer " + self.whatsapp_token

		self.cursor.execute("select * from users where user_id = ?", self.user_id)
		current_user = self.cursor.fetchone()
		self.conn.close()

		if user:
			# * Get all data based on user_id
			print(current_user)
			self.whatsapp_token = current_user['whatsapp_key']
			self.whatsapp_id = current_user['whatsapp_id']
			self.sheet_id = current_user['sheet_id']
			self.last_row = current_user['last_row'] 
			self.url = f"https://graph.facebook.com/v21.0/{self.whatsapp_id}/messages"

			with open(f"message_templates/{user_id}.json") as f:
				self.message_template = json.load(f.read())

		else:
			raise ValueError(f"No user has been found with {self.user_id} ID. Check if data is correct or check DB!")


	# TODO: Import the message template from templates folder
	# * Inside the vps there will be a templates folder with every users preffered message template
	# * I.E: message_templates/{user_id}.json
	template = {}
	
	# !! Figure it out shithead
	# creds = ServiceAccountCredentials.from_json_keyfile_dict(self.sheet_creds, scope)
	# client = gspread.authorize(creds)
	# sheet = client.open_by_key(self.sheet_id)

	def updateLastLine():
		# * Inside the db file upadte 

		pass

	def listener():
		# !! This function is critical
		# TODO: Based on the last row inside the db for the respective user.
		# TODO: Check if there is a difference between the no of lines inside gSheet and in DB
		pass


if __name__ == "__main__":
	initializaEventsDB()
	initializeUserDB()
