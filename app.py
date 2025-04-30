from flask import Flask, redirect, request, session, url_for, render_template, jsonify
import google.oauth2
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import sqlite3

from datetime import datetime, timedelta
from dateutil.relativedelta import	relativedelta

import os
import subprocess
from time import sleep

from backend import User # * My creation

# Your pre-shared token – make sure this matches the one you set in Meta dashboard
VERIFY_TOKEN = "my_super_secret_token"

app = Flask(__name__)
with open('secret_key.txt', 'r') as f:
	app.secret_key = f.read()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 
	"openid"]

_user_cache = {}

def get_user_id_DB(email:str) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
		result = cursor.fetchone()
		if result:
			return result[0]
		else:
			raise ValueError("No matching data found!")

def get_len_message_sorted(user_id:int, event_type:str, timestamp: str) -> int:
	if(event_type == "sent"):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				SELECT COUNT(*) FROM message_events 
				WHERE user_id = ?
				AND timestamp > ?;
			""", (user_id, timestamp))

			count = cursor.fetchone()[0]
			# print(count)
			return count
	elif (event_type == "seen"):
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				SELECT COUNT(*) FROM message_events 
				WHERE user_id = ?
				AND event_type IN ('seen', 'responded')
				AND timestamp > ?;
			""", (user_id, timestamp))

			count = cursor.fetchone()[0]
			# print(count)
			return count
		
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			SELECT COUNT(*) FROM message_events 
			WHERE user_id = ?
			AND event_type = ?
			AND timestamp > ?;
		""", (user_id, event_type, timestamp))

		count = cursor.fetchone()[0]
		# print(count)
		return count

def calculate_date_range(subtraction_value: str):
	now = datetime.now()
	
	cases = {
		"one_day": now - timedelta(days=1),
		"two_day": now - timedelta(days=2),
		"three_day": now - timedelta(days=3),
		"five_day": now - timedelta(days=5),
		"one_week": now - timedelta(weeks=1),
		"two_week": now - timedelta(weeks=2),
		"one_month": now - relativedelta(months=1),  # Correctly handles different month lengths
		"six_month": now - relativedelta(months=6),  # Accounts for varying month lengths
		"one_year": now - relativedelta(years=1)  # Correctly handles leap years
	}
	
	result = cases.get(subtraction_value)
	return result.strftime("%Y-%m-%d %H:%M:%S") if result else "Invalid subtraction value"

def save_credentials_to_db(user_id : int, credentials : dict):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE users SET credentials_json = ? WHERE user_id = ?;
		""", (credentials, user_id))
		conn.commit()

def load_credentials_from_db(user_id : int):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT credentials_json FROM users WHERE user_id = ?", (user_id, ))
		row = cursor.fetchone()
		if row:
			return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
		return None

def refresh_credentials(user_id: int) :
	creds = load_credentials_from_db(user_id)
	if not creds:
		raise Exception(f"No credentials found for user: {user_id}")
	
	if creds.expired and creds.refresh_token:
		creds.refresh(Request())
		save_credentials_to_db(user_id, creds)
		
	return creds

def getUserID():
	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	return user_id

def retUser(user_id: int):
	if user_id not in _user_cache:
		_user_cache[user_id] = User(user_id)
	return _user_cache[user_id]

def checkAccountByEmail(email: str) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))
		exists = cursor.fetchone() is not None

		if exists: return True
		return False

@app.route("/")
def index():
	return render_template("login/index.html")

@app.route("/logout")
def logout():
	if 'credentials' in session:
		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		print(f"[{now}]--- Logging user out ---")
	session.clear()
	return redirect(url_for('index'))

@app.route("/login")
def login():
	session.clear()
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES
	)
	flow.redirect_uri = url_for("callback", _external=True)
	authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent', include_granted_scopes='true')
	session["state"] = state
	return redirect(authorization_url)

@app.route("/callback")
def callback():
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES, state=session["state"]
	)
	flow.redirect_uri = url_for("callback", _external=True)

	flow.fetch_token(authorization_response=request.url)
	credentials = flow.credentials

	session["credentials"] = credentials.to_json()
	
	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	# * Save credentials to DB
	save_credentials_to_db(user_id, session['credentials'])

	return redirect(url_for("read_sheet"))

@app.route('/submit_json', methods=['POST'])
def submit_json():
	data = request.get_json()
	if not data or "choice" not in data:
		return jsonify({"error" : "Invalid request"}), 400
	# print("[ JSON Received from js Code ] : ", data['choice'])

	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	received_data = data['choice']
	time_interval = calculate_date_range(received_data)
	sent_count = get_len_message_sorted(user_id, 'sent', time_interval)
	seen_count = get_len_message_sorted(user_id, 'seen', time_interval)
	resp_count = get_len_message_sorted(user_id, 'responded', time_interval)

	# print( {
	# 	"sent_count" : sent_count,
	# 	"seen_count" : seen_count,
	# 	"resp_count" : resp_count,
	# 	"message" : "Succes!"
	# })

	return jsonify( {
		"sent_count" : sent_count,
		"seen_count" : seen_count,
		"resp_count" : resp_count,
		"message" : "Succes!"
	})

@app.route('/status', methods=['POST'])
def status():
	ps = retUser(getUserID()).get_script_status()
	value = "Running" if ps == True else "Stopped"
	return jsonify({'status' : value })

# ! When pressing the stop button it takes a lot of time to process 
# ! - may be caused by the current error where it doesn't load properly the sheet (backend.py)
@app.route('/start-stop', methods=['POST'])
def start_stop():
	data = request.get_json()
	print(data)
	if not data or "choice" not in data or 'credentials' not in session:
		return jsonify({"error" : "Invalid request"}), 400

	received_data = data['choice']
	if received_data == '0':
		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		print(f"[{now}][User {getUserID()}] Stopping script")
		retUser(getUserID()).stop_listener()
		return jsonify({"message" : "Stopped script"}), 200
	
	elif received_data == '1':
		now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
		print(f"[{now}][User {getUserID()}] Starting script")
		retUser(getUserID()).launch_listener()
		return jsonify({"message" : "Started script"}), 200
	
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	print(f"[{now}][User {getUserID()}] Error invalid value provided")
	return jsonify({"error" : "Invalid value provided"}), 400

@app.route("/user_info")
def read_sheet():
	if 'credentials' not in session:
		return redirect(url_for('index'))

	user = retUser(getUserID())
	script_status = user.get_script_status()
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	print(f"[{now}][User {getUserID()}] Script is running") if script_status else print(f"[{now}][User {getUserID()}] Script is stopped")

	return render_template("dashboard/index.html", script_st = script_status)

@app.route("/profile")
def profile():
	return render_template('profile/index.html')

@app.route("/profile-updates", methods=['GET', 'POST'])
def profile_updates():
	if 'credentials' not in session:
		return 401
	else:
		if request.method == 'GET':
			user = retUser(getUserID())
			response = {
				"email": user.get_user_data()[4],
				"whatsapp_number": user.get_user_data()[3],
				"whatsapp_token": user.get_user_data()[2],
				"google_sheetID": user.get_user_data()[1] 
			}
			return jsonify(response), 200
		elif request.method == 'POST':
			data = request.get_json()
			# TODO: Update user data
			if data['choice'] == 0: # * choice = 0 -> Check for email in db
				received_data = data['email']
				result = None
				if(checkAccountByEmail(received_data)): 
					result = "true"
				else: 
					result = "false"
				return jsonify({"result": result}), 200
			elif data['choice'] == 1: # * choice = 1 -> Update values for user
				vEmail = data['email']
				vWToken = data['wToken']
				vWNumber = data['wNumber']
				vGSheetID = data['gSheetID']

				if(checkAccountByEmail(vEmail) == True): # * Account exists, update current values
					print("Account found with email:", vEmail)
					current_user = retUser(get_user_id_DB(vEmail))
					if(current_user.update_account_details(vEmail, vWNumber, vWToken, vGSheetID)):
						return jsonify({ "result" : "succes" }), 200
					else: 
						return jsonify({"result" : "error"}), 500
				else: # * Create new account
					print("Account not found")
					return jsonify({"result" : "not_found"}), 404
				# return jsonify({ "result" : "succes" }), 200
		else:
			return 405

@app.route("/webhook", methods=['POST'])
def webhook():
	if request.method == 'GET':
		mode = request.args.get('hub.mode')
		token = request.args.get('hub.verify_token')
		challenge = request.args.get('hub.challenge')

		if mode == 'subscribe' and token == VERIFY_TOKEN:
			print("Webhook verified successfully!")
			return challenge, 200
		else:
			print("Webhook verification failed.")
			return "Forbidden", 403
	elif request.method =='POST':
		data = request.json
		# TODO Implement data collection and recognition idk man...
	else:
		return jsonify("Method not allowed"), 405
	return 200

if __name__ == "__main__":
	# app.run(debug=True)  # Enables HTTPS for local testing
	app.run(port=5100,ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True)  # Enables HTTPS for local testing
	
