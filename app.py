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

app = Flask(__name__)
with open('secret_key.txt', 'r') as f:
	app.secret_key = f.read()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 
	"openid"]

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

@app.route("/")
def index():
	return render_template("login/index.html")

@app.route("/logout")
def logout():
	if 'credentials' in session:
		print("--- Logging user out ---")
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

@app.route('/change_status', methods=['POST'])
def change_status():
	...

@app.route('/start')
def start():
	...

@app.route('/stop')
def stop():
	...

@app.route("/user_info")
def read_sheet():
	if 'credentials' not in session:
		return redirect(url_for('index'))
	
	# credentials_info = json.loads(session['credentials'])
	# credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	user = User(user_id)
	script_status = user.get_script_status()
	

	return render_template("dashboard/index.html", script_st = script_status)

if __name__ == "__main__":
	# app.run(debug=True)  # Enables HTTPS for local testing
	app.run(port=5100,ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True)  # Enables HTTPS for local testing
	
