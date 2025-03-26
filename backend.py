
import requests
import json
import gspread
import logging
import time
from os.path import isfile
from logging.handlers import RotatingFileHandler
from oauth2client.service_account import ServiceAccountCredentials
from discord_webhook import DiscordWebhook

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

class user:
	# Constructor
	def __init__(self, user_id):
		self.user_id = user_id

	def loadCredentialsFromDb(self):
		# TODO: After getting user_id, get all variables under this function from db based on user_id
		global meta_id, sheet_creds, sheet_id
		meta_id = None
		sheet_creds = None
		sheet_id = None
		pass
	
	meta_id = None
	sheet_creds = None
	sheet_id = None

	scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
	url = f"https://graph.facebook.com/v21.0/{meta_id}/messages"
	
	# TODO: Import the message template from templates folder
	# * Inside the vps there will be a templates folder with every users preffered message template
	# * I.E: message_templates/{user_id}.json
	template = {}
	
	# !! Figure it out shithead
	creds = ServiceAccountCredentials.from_json_keyfile_dict(sheet_creds, scope)
	client = gspread.authorize(creds)
	sheet = client.open_by_key(sheet_id)

	def updateLastLine():
		# * Inside the db file upadte 
		pass

	def listener():
		# !! This function is critical
		# TODO: Based on the last row inside the db for the respective user.
		# TODO: Check if there is a difference between the no of lines inside gSheet and in DB
		pass
