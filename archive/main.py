# The limit on google sheets api reads in 500.000/day
# 86.400 seconds in a day
# -> 0.2 requests per seconds
# Will multiply it by 10 just to be safe
# After 21600 check I get log =~ 12 hours

import requests
import json
import gspread
import logging
import time
from os.path import isfile
from logging.handlers import RotatingFileHandler
from oauth2client.service_account import ServiceAccountCredentials
from discord_webhook import DiscordWebhook

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

url = "https://graph.facebook.com/v21.0/469064916301145/messages"

webhookUrl = "https://discord.com/api/webhooks/1332767592292552724/CN1fnoDt-HpdMbKVdv7E0CDFmFQOxdPwR26EqvZS2d5vCiOPqiHVrOk7Gw1kdf8QwAuS"

discordHeaders = {
	"Content-Type": "application/json",
	"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"
}

headers = {
	"Content-Type" : "application/json",
	"Authorization" : None
}

template = {
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": None,
  "type": "template",
  "template": {
    "name": "testare",
    "language": {
      "code": "ro"
    },
    "components": [
      {
        "type": "body",
        "parameters": [
          {
            "type": "text",
            "text": None
          }
        ]
      }
    ]
  }
}

# Configure the RotatingFileHandler
log_handler = RotatingFileHandler(
    "archive/logfile.log",  # Log file name
    maxBytes=1_000_000,  # Maximum file size in bytes (1 MB in this example)
    backupCount=0  # No backup files; overwrite the same file
)

logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
    handlers=[log_handler]  # Add the rotating handler
)

with open("archive/key.json", "r") as f:
	data = json.loads(f.read())
	headers['Authorization'] = 'Bearer ' + data['whatsappKey']

	global sheetCreds
	sheetCreds = data['sheetsKey']

	global sheetName
	sheetName = data['sheetName']
	logging.info(f"Succesfully read WhatsappKey.txt -> {headers['Authorization']}")


creds = ServiceAccountCredentials.from_json_keyfile_dict(sheetCreds, scope)
client = gspread.authorize(creds)

sheet = client.open(sheetName).sheet1

def precheck():
	if not isfile("archive/remember.txt"):
		with open("archive/remember.txt", "w") as f:
			f.write("2")

# * Modify the last line  for the next run of the program
def updateLastLine(nameCol):
	f = open("archive/remember.txt", 'r')
	t = int(f.read())
	f.close()
	t = t + len(nameCol)  # ! This points to last contact card + 1
	logging.info(f"New line is {t}")
	f = open('archive/remember.txt', 'w')
	f.write(str(t))

def sendDiscordLog():
	#Create a Discord webhook object
	webhook = DiscordWebhook(url=webhookUrl)

	#Add the file or files to the embed
	with open('logfile.log', 'rb') as f: 
		file_data = f.read() 
	webhook.add_file(file_data, 'logfile.log')

	#Send the webhook
	response = webhook.execute()
	if(response.status_code == 200): logging.info("[200]Sent logfile.log to admin")
	else: logging.error(f"[{response.status_code}]{response.text}")

def transformPhoneNumber(phoneNr):
	phoneNr = str(phoneNr)
	if(phoneNr[0] == '7'): return phoneNr
	phoneNumber = phoneNr
	phoneNumber = phoneNr[4:7]+phoneNr[8:11]+phoneNr[12:15]
	return phoneNumber

def listener():
	lastNumber = None
	with open("archive/remember.txt", 'r') as f:
		lastNumber = int(f.read())
	
	nameCol = sheet.get(f'B{lastNumber}:B')

	# * When the row is empty, length of nameCol is 1 and len of nameCol[0] is 0
	print("Waiting...")
	if(len(nameCol) >=1 and len(nameCol[0]) != 0):
		print("nameCol : ", nameCol) 
		# print("Length : ", len(nameCol))
		# print('nameCol[0] : ', nameCol[0])
		# print('Length nameCol[0] : ', len(nameCol[0]))
		executor()
		# print("-----------------")

def executor():
	lastNumber = None
	with open("archive/remember.txt", 'r') as f:
		lastNumber = int(f.read())

	nameCol = sheet.get(f'C{lastNumber}:C')
	phNrCol = sheet.get(f'D{lastNumber}:D', value_render_option='FORMULA')

	print(phNrCol)

	for i in range(len(nameCol)): # Go through every user and send them a custom message
		print("index : ", i)
		template['to'] = '40' + transformPhoneNumber(phNrCol[i][0])
		template['template']['components'][0]['parameters'][0]['text'] = nameCol[i][0]
		# print(f"{template['to']} -> {template['template']['components'][0]['parameters'][0]['text']}") # Actual live data taken from sheets
		response = requests.request("POST", url, data=json.dumps(template), headers=headers)
		if(response.status_code == 200):
			logging.info(f"[{response.status_code}] Sent {nameCol[i][0]} : 40{phNrCol[i][0]} template message named - {template['template']['name']}")
		else:
			logging.error(f"[{response.status_code}] {response.text}")
		print(response.text)
		print(response.status_code)
	updateLastLine(nameCol)
	logging.info("------- SESION END -------")

def main():
	precheck()
	x = 0 
	while True:
		try:
			x += 1
			listener()
			time.sleep(2)
			# TODO: After 21600 sessions send the log through discord to custom server
			if x == 21600: 
			# if x == 10: # For testing
				x = 0
				sendDiscordLog()
			# print(x)
		except KeyboardInterrupt:
			print("\nStopping program")
			quit()

if __name__ == '__main__':
	main()