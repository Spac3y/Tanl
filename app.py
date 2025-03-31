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
		sleep(5)  # Check every 5 seconds

def get_user_id_DB(email:str) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
		result = cursor.fetchone()
		if result:
			return result[0]
		else:
			raise ValueError("No matching data found!")

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
	print(session["credentials"])

	return redirect(url_for("read_sheet"))

@app.route("/read_sheet")
def read_sheet() -> str:
	if "credentials" not in session:
		return redirect(url_for('index'))
	
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	# print(f"!!{email}!!")

	gc = gspread.authorize(credentials)
	sheet_id = "1iz9IkmMlmFr3Zykjrqot0Y_0PQsQw3ZWZR7JZ4YFkH0"
	# # ! Figure out where to put sheet_range
	# sheet_range = ""

	sh = gc.open_by_key(sheet_id)
	worksheet = sh.sheet1
	data = worksheet.get_all_records()

	return (str(data))

@app.route("/dashboard")
def admin_dashboard():
	if 'credentials' not in session:
		return redirect(url_for('index'))
	return render_template("dashboard/index.html")

def credentials_to_dict(credentials) -> dict:
	return {
		"token": credentials.token,
		"refresh_token": credentials.refresh_token,
		"token_uri": credentials.token_uri,
		"client_id": credentials.client_id,
		"client_secret": credentials.client_secret,
		"scopes": credentials.scopes,
	}

if __name__ == "__main__":
	# app.run(debug=True)  # Enables HTTPS for local testing
	app.run(port=5100,ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True)  # Enables HTTPS for local testing
	
