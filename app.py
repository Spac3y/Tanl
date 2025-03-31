from flask import Flask, redirect, request, session, url_for, render_template
import google.oauth2
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import google.auth.transport.requests
import gspread
import json
import sqlite3

import os
import subprocess
from time import sleep

from backend import User

processes = {}

app = Flask(__name__)
with open('secret_key.txt', 'r') as f:
	app.secret_key = f.read()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 
	"openid"]

def start_script(user_id:int):
	if user_id in processes:
		return f"Script for user {user_id} is already running."

	process = subprocess.Popen(["python3", "your_script.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	processes[user_id] = process
	return f"Started script for user {user_id}"

def stop_script(user_id:int):
	if user_id not in processes:
		return f"No running script for user {user_id}."

	process = processes.pop(user_id)
	process.terminate()  # Graceful stop
	process.wait()  # Ensure it's properly stopped
	return f"Stopped script for user {user_id}"

def check_script_status(user_id:int):
	if user_id in processes and processes[user_id].poll() is None:
		return f"Script for user {user_id} is running."
	return f"No running script for user {user_id}."

def monitor_and_restart():
	while True:
		for user_id, process in list(processes.items()):
			if process.poll() is not None:  # If process has ended
				print(f"Restarting script for user {user_id}")
				start_script(user_id)
		sleep(30)  # Check every 30 seconds

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
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			SELECT COUNT(*) FROM message_events 
			WHERE user_id = ?
			AND event_type = ?
			AND timestamp > ?;
		""", (user_id, event_type, timestamp))

		count = cursor.fetchone()[0]
		print(count)
		return count

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
	# print(session["credentials"])

	# return redirect(url_for("admin_dashboard"))
	return redirect(url_for("read_sheet"))

@app.route("/user_info")
def read_sheet():
	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)
	print(f"USER ID: {user_id}")

	# user = User(user_id, credentials)
	# print(f"SHEET ID:{user.sheet_id}")
	# user.sender()

	var = get_len_message_sorted(user_id,'sent', '2025-03-31 15:00:00')
	return render_template("dashboard/index.html", my_variable=var)

if __name__ == "__main__":
	# app.run(debug=True)  # Enables HTTPS for local testing
	app.run(port=5100,ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True)  # Enables HTTPS for local testing
	
