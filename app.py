from flask import Flask, redirect, request, session, url_for
import google.oauth2
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
import gspread
import json

import os
import subprocess
from time import sleep

processes = {}

app = Flask(__name__)
app.secret_key = '0e90999e0328b102327213dafd270da2d2d903c2f51d7468'
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.file"]

def start_script(user_id):
	if user_id in processes:
		return f"Script for user {user_id} is already running."

	process = subprocess.Popen(["python3", "your_script.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	processes[user_id] = process
	return f"Started script for user {user_id}"

def stop_script(user_id):
	if user_id not in processes:
		return f"No running script for user {user_id}."

	process = processes.pop(user_id)
	process.terminate()  # Graceful stop
	process.wait()  # Ensure it's properly stopped
	return f"Stopped script for user {user_id}"

def check_script_status(user_id):
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

@app.route("/")
def index():
	return '<a href="/login">Login with Google</a>'

@app.route("/login")
def login():
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES
	)
	flow.redirect_uri = url_for("callback", _external=True)
	authorization_url, state = flow.authorization_url()
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
	session["credentials"] = credentials_to_dict(credentials)

	return redirect(url_for("read_sheet"))

@app.route("/read_sheet")
def read_sheet():
	if "credentials" not in session:
		return redirect(url_for("login"))
	
	credentials = google.oauth2.credentials.Credentials(**session["credentials"])
	gc = gspread.authorize(credentials)
	
	# ! Get sheet_id from DB
	sheet_id = "1iz9IkmMlmFr3Zykjrqot0Y_0PQsQw3ZWZR7JZ4YFkH0"
	sh = gc.open_by_key(sheet_id)
	worksheet = sh.sheet1
	
	data = worksheet.get_all_records()

	return str(data)

	# credentials = google.oauth2.credentials.Credentials(**session["credentials"])
	# service = googleapiclient.discovery.build("sheets", "v4", credentials=credentials)

	# sheet_id = "1iz9IkmMlmFr3Zykjrqot0Y_0PQsQw3ZWZR7JZ4YFkH0"  #TODO: Replace with user input

	# sheet = service.spreadsheets()
	# result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
	# return str(result.get("values", []))

def credentials_to_dict(credentials):
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
	app.run(ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True)  # Enables HTTPS for local testing
	
