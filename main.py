import requests
import json
import gspread
import logging
from logging.handlers import RotatingFileHandler
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

url = "https://graph.facebook.com/v21.0/469064916301145/messages"

headers = {
	"Content-Type" : "application/json",
	"Authorization" : None
}

# Configure the RotatingFileHandler
log_handler = RotatingFileHandler(
    "logfile.log",  # Log file name
    maxBytes=1_000_000,  # Maximum file size in bytes (1 MB in this example)
    backupCount=0  # No backup files; overwrite the same file
)

logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
    handlers=[log_handler]  # Add the rotating handler
)

with open("whatsappKey.txt", 'r') as f:
	headers['Authorization'] = "Bearer " + f.read()

logging.info(f"Succesfully read WhatsappKey.txt -> {headers['Authorization']}")

dataJson = {
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

creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
client = gspread.authorize(creds)
logging.info(f"Succesfully read key.json")


with open("remember.json", 'r') as f:
	temp = json.loads(f.read())
	global sheetName
	sheetName = temp['sheetName']

sheet = client.open(sheetName).sheet1

# * Modify the last line  for the next run of the program
def updateLastLine():
	f = open("remember.json", 'r')
	t = json.loads(f.read())
	f.close()
	t['lastLine'] = t["lastLine"] + len(nameCol) - 1 # ! This point to last contact card
	f = open('remember.json', 'w')
	f.write(json.dumps(t))

# * The lettering stays constant, the left number is imported from file
lastNumber = None
with open("remember.json") as f:
	d = json.loads(f.read())
	lastNumber = d['lastLine']

nameCol = sheet.get(f'C{lastNumber}:C')
phNrCol = sheet.get(f'D{lastNumber}:D')

# TODO: Implement code logging.
for i in range(len(nameCol)): # Go through every user and send them a custom message
	dataJson['to'] = '40' + phNrCol[i][0]
	dataJson['template']['components'][0]['parameters'][0]['text'] = nameCol[i][0]
	print(f"{dataJson['to']} -> {dataJson['template']['components'][0]['parameters'][0]['text']}") # Actual live data taken from sheets
	response = requests.request("POST", url, data=json.dumps(dataJson), headers=headers)
	if(response.status_code == 200):
		logging.info(f"[{response.status_code}] Sent {nameCol[i][0]} : 40{phNrCol[i][0]} template message named - {dataJson['template']['name']}")
	else:
		logging.error(f"[{response.status_code}] {response.text}")
	# print(response.text)
	print(response.status_code)
