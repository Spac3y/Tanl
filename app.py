from flask import Flask, redirect, request, session, url_for, render_template, jsonify
import google.oauth2
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import sqlite3
import os

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# for interactive message
import smtplibW
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend import User, createAccount # * My creation


# *: Implement unit tests
# * 1. Send messages
# * 2. Whatsapp webhook verification
# * 3. Connection to google sheets
# * 4. Get user data from database

# ! When accesing through ngrok i get uri missmatch error FIX!!!!
# * this error is caused because i have a dynamic url. Need to get domain for static webhook url

# Whatsapp webhook verification token
VERIFY_TOKEN = "my_super_secret_token"

SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
APP_PASSWORD = ""

subject = "Client nou interesat de produs!!"
email_message = MIMEMultipart()
email_message['From'] = SENDER_EMAIL
email_message['To'] = RECEIVER_EMAIL
email_message['Subject'] = subject

app = Flask(__name__, static_folder='static', template_folder='templates')
with open('secret_key.txt', 'r') as f:
	app.secret_key = f.read()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", 
	"openid"]

_user_cache = {}

def getCurrentTime():
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	return now

# *
def get_user_id_DB(email:str) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
		result = cursor.fetchone()
		if result:
			return result[0]
		else:
			return None

# *
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
		return count

def getEmail() -> str:
	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	try:
		# * Get the users email
		service = build('people', 'v1', credentials=credentials)
		profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
		email = profile.get('emailAddresses', [])[0].get('value')
		return email
	except google.auth.exceptions.RefreshError as e:
		print(f"[{getCurrentTime()}] Error refreshing credentials: {e}")
		return redirect(url_for('login'))

def getUserID():
	email =  getEmail()
	user_id = get_user_id_DB(email)
	if user_id is not None:
		return [1, user_id]
	else:
		print(f"[{email}]User not found in DB but email is accepted | Redirect -> Create account")
		return [-1, email]

def retUser(user_id: int):
	if user_id not in _user_cache:
		_user_cache[user_id] = User(user_id)
	return _user_cache[user_id]

# *
def checkAccountByEmail(email: str) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))
		exists = cursor.fetchone() is not None

		if exists: return True
		return False

# *
def save_credentials_to_db(user_id : int, credentials : dict):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE users SET credentials_json = ? WHERE user_id = ?;
		""", (credentials, user_id))
		conn.commit()

# *
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

# *
def updateMessageEvent(new_type:str, message_id: str, conversation_id:str, is_response:bool, user_id:int) -> bool:
	cutoff_date = (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S")
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		if is_response and message_id == 'none': 
			cursor.execute("UPDATE message_events SET event_type='responded' WHERE user_id = ?, message_id = ? ", (user_id, conversation_id))
			conn.commit()
			return True

		if new_type == "sent":
			cursor.execute("UPDATE message_events SET message_id = ? WHERE user_id = ? AND message_id = ? AND message_id = 'none' ", (conversation_id, user_id, message_id))

		cursor.execute("UPDATE message_events SET event_type = ? WHERE user_id = ? AND message_id = ? AND timestamp > ? ",
			(new_type, user_id, message_id, cutoff_date))

		if cursor.rowcount == 0: # * Check all messages one week old
			cursor.execute("UPDATE message_events SET event_type = ? WHERE user_id = ? AND message_id = ?",
			(new_type, user_id, message_id))
			if cursor.rowcount == 0: # * Check all messages
				return False
			
		conn.commit()
		return True

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

#* Functions for first chart
def getCustomValues(interval, user_id: int):
	now = datetime.now()
	results = []

	with sqlite3.connect('database.db') as conn:
		cursor = conn.cursor()

		def count_for_range(start, end):
			cursor.execute("SELECT COUNT(*) FROM message_events WHERE timestamp BETWEEN ? AND ? AND user_id = ?",
						(start.isoformat(), end.isoformat(), user_id))
			return cursor.fetchone()[0] or 0

		# Map intervals to number of hours
		interval_map = {
			'one_day': 24,
			'two_day': 48,
			'three_day': 72,
			'five_day': 120,
			'one_week': 7 * 24,
			'two_week': 14 * 24,
			'one_month': 30 * 24,
			'six_month': 180 * 24,
			'one_year': 365 * 24
		}

		if interval not in interval_map:
			raise ValueError("Unknown interval")

		total_hours = interval_map[interval]
		bucket_count = 10  # Between 5 and 7
		bucket_size = total_hours // bucket_count

		start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=total_hours)

		for i in range(bucket_count):
			bucket_start = start_time + timedelta(hours=i * bucket_size)
			bucket_end = bucket_start + timedelta(hours=bucket_size)
			
			# Format label depending on the length of the bucket
			if total_hours <= 72:
				label = bucket_start.strftime("%d %b %H:%M")
			elif total_hours <= 30 * 24:
				label = bucket_start.strftime("%d %b")
			else:
				label = bucket_start.strftime("%b %Y")
			
			count = count_for_range(bucket_start, bucket_end)
			results.append({'label': label, 'value': count})

	return results

#* Functions for second chart 
def getMonthlyValues(user_id: int):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute('''
		WITH months(month_number, month_name) AS (
		VALUES
			('01', 'January'), ('02', 'February'), ('03', 'March'),
			('04', 'April'),   ('05', 'May'),      ('06', 'June'),
			('07', 'July'),    ('08', 'August'),   ('09', 'September'),
			('10', 'October'), ('11', 'November'), ('12', 'December')
		)
		SELECT 
		COALESCE(count_table.count, 0) AS count
		FROM months
		LEFT JOIN (
		SELECT 
			strftime('%m', timestamp) AS month_number,
			COUNT(*) AS count
		FROM message_events
		WHERE user_id = ?
		GROUP BY month_number
		) AS count_table
		ON months.month_number = count_table.month_number
		ORDER BY months.month_number;
		''', (user_id,))

		rows = cursor.fetchall()
		return [count for (count,) in rows]

def handlePreconfResponse(data):
	# * Check for preconfigured response
	try:
		messages = data['entry'][0]['changes'][0]['value']['messages']
		# * Check if message is preconfigured button message
		if not messages:
			return "No messages", 200

		msg = messages[0]
		if msg['type'] != 'button':
			return "Ignored: Not a button", 200

		button_message = msg['button']['payload']
		phone = msg['from']

		# if button_message != "I'm interested!":
		# 	return None
			
		print("------------------------")
		print(phone, button_message, type(button_message))

		# * Send email with the button message and phone number
		try:
			body = str(phone) + " | " + button_message
			email_message.attach(MIMEText(body, 'plain'))
			with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
				server.login(SENDER_EMAIL, APP_PASSWORD)
				server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_message.as_string())
				print("✅ Email sent successfully!")
		except Exception as e:
			print("❌ Error:", e)

		return "Button processed", 200

	except Exception as e:
		return f"Error: {str(e)}", 400

@app.route('/')
def design():
	if 'credentials' not in session:
		return redirect(url_for('login'))
	
	user_id = getUserID()

	if getUserID()[0] == -1:
		return redirect(url_for('profile', force_redirect=1, email=user_id[1]))

	user = retUser(user_id[1])
	script_status = user.get_script_status()
	# print(f"[{getCurrentTime()}][User {user_id[1]}] Script is running") if script_status else print(f"[{getCurrentTime()}][User {getUserID()[1]}] Script is stopped")
	return render_template("design/index.html", script_st = script_status), 200

# *
@app.route("/login")
def login():
	if 'credentials' in session:
		print(f"[{getCurrentTime()}]--- Logging user out ---")
	session.clear()
	return render_template("login/index.html")

# *
@app.route("/logout")
def logout():
	if 'credentials' in session:
		print(f"[{getCurrentTime()}]--- Logging user out ---")
	session.clear()
	return redirect(url_for('design'))

@app.route("/google_login")
def google_login():
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

	return redirect(url_for("design"))

# *
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
	price_lead = retUser(getUserID()[1]).getPriceLead()
	monthly_values = getMonthlyValues(user_id)
	custom_values = getCustomValues(received_data,user_id)

	return jsonify( {
		"sent_count" : sent_count,
		"seen_count" : seen_count,
		"resp_count" : resp_count,
		"price-lead" : price_lead,
		"monthly_values" : monthly_values,
		"custom_values" : custom_values,
		"result" : "succes"
	})

# *
@app.route('/status', methods=['POST'])
def status():
	ps = retUser(getUserID()[1]).get_script_status()
	thread_status = retUser(getUserID()[1]).is_thread_running()
	value = None

	if thread_status and ps:
		value = "Running"
	elif ps and not thread_status:
		value = "Stopped"
		retUser(getUserID()[1]).update_script_status("stopped")
	elif not ps and thread_status:
		value = "Running"
		retUser(getUserID()[1]).update_script_status("running")
	elif not ps and not thread_status:
		value = "Stopped"
	else:
		value = "Error"

	return jsonify({'status' : value })

# *
@app.route('/start-stop', methods=['POST'])
def start_stop():
	data = request.get_json()
	if not data or "choice" not in data or 'credentials' not in session:
		return jsonify({"error" : "Invalid request"}), 400

	received_data = data['choice']
	if received_data == '0':
		retUser(getUserID()[1]).stop_listener()
		return jsonify({"message" : "Stopped script"}), 200
	
	elif received_data == '1':
		print(f"[{getCurrentTime()}][User {getUserID()[1]}] Starting script")
		retUser(getUserID()[1]).launch_listener()
		return jsonify({"message" : "Started script"}), 200
	
	print(f"[{getCurrentTime()}][User {getUserID()[1]}] Error invalid value provided")
	return jsonify({"error" : "Invalid value provided"}), 400

@app.route("/user_info")
def read_sheet():
	if 'credentials' not in session:
		return redirect(url_for('index'))
	
	user_id = getUserID()

	if getUserID()[0] == -1:
		return redirect(url_for('profile', force_redirect=1, email=user_id[1]))

	user = retUser(user_id[1])
	script_status = user.get_script_status()
	print(f"[{getCurrentTime()}][User {user_id[1]}] Script is running") if script_status else print(f"[{getCurrentTime()}][User {getUserID()[1]}] Script is stopped")

	return render_template("dashboard/index.html", script_st = script_status)

# TODO: When creating account put email inside cookie not url
@app.route("/profile")
def profile():
	force_redirect = request.args.get('force_redirect', default=0, type=int)
	email = request.args.get('email', default=getEmail(), type=str)
	return render_template('profile/index.html', force_redir = force_redirect, email = email)

# *
@app.route("/profile-updates", methods=['GET', 'POST'])
def profile_updates():
	if 'credentials' not in session:
		return 401
	else:
		if request.method == 'GET':
			user_data = retUser(getUserID()[1]).get_user_data()
			message_limit = retUser(getUserID()[1]).get_message_limit()
			response = {
				"email": user_data[4],
				"whatsapp_number": user_data[3],
				"whatsapp_token": user_data[2],
				"google_sheetID": user_data[1],
				"price_lead": user_data[7],
				"template_name" : user_data[8],
				"column_name" : user_data[9],
				"column_phone" : user_data[10],
				"limit_enabled" : message_limit[1],
				"message_limit" : message_limit[2]
			}
			return jsonify(response), 200
		elif request.method == 'POST':
			data = request.get_json()
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
				vPriceLead = data['price_lead']
				vTemplateName = data['tName']
				vNameCol = data['cName']
				vPhoneCol = data['cPhone']
				limitEnabled = data['limitEnabled']
				mLimit = data['mLimit']

				if(checkAccountByEmail(vEmail) == True): # * Account exists, update current values
					current_user = retUser(get_user_id_DB(vEmail))
					if(current_user.update_account_details(vEmail, vWNumber, vWToken, vGSheetID, vPriceLead, vTemplateName, vNameCol, vPhoneCol) and current_user.update_message_limit(limitEnabled, mLimit)):
						current_user.refresh()
						return jsonify({ "result" : "success" }), 200
					else: 
						return jsonify({"result" : "error"}), 500
				else: # * Create new account
					print("Account not found")
					return jsonify({"result" : "not_found"}), 404
				
			elif data['choice'] == 2: # * choice = 2 -> Create a new account for accepted user
				vEmail = data['email']
				vWToken = data['wToken']
				vWNumber = data['wNumber']
				vGSheetID = data['gSheetID']
				vPriceLead = data['price_lead']
				vTemplateName = data['tName']
				vNameCol = data['cName']
				vPhoneCol = data['cPhone']
				if(createAccount(vGSheetID, vWToken, vWNumber, vEmail, vPriceLead)): # * accout created in db
					return jsonify({ "result" : "success"}), 200
				return jsonify({ "result" : "false"}), 500
		else:
			return "Method not allowed",405

# *
@app.route('/webhook', methods=['GET', 'POST'])
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
			return "Not found", 404

	elif request.method == 'POST':
		data = request.json
		conversation_id =  data['entry'][0]['id']
		is_response = False

		if 'contacts' in data['entry'][0]['changes'][0] and 'messages' in data['entry'][0]['changes'][0]:
			is_response = True
			message_id = 'none'
			# * will be used later when implementing whatsapp client side
			# message_id = data['entry'][0]['changes'][0]['value']['messages'][0]['id']
			# client_name = data['entry'][0]['changes'][0]['value']['contacts'][0]['profile']['name']
			# client_phone = data['entry'][0]['changes'][0]['value']['contacts'][0]['wa_id']
		else:
			status = data['entry'][0]['changes'][0]['value']['statuses'][0]['status']
			message_id = data['entry'][0]['changes'][0]['value']['statuses'][0]['id']
		
		if(updateMessageEvent(status, message_id, conversation_id, is_response,  getUserID[1]) == True):
			return jsonify({"status" : "success"}), 200
		return jsonify({"error" : "Internal server error"}), 500

		handlePreconfReponse()

# *
@app.errorhandler(404)
def page_not_found(e):
	return render_template('404/index.html', error_message=str(e)), 404

# *
@app.errorhandler(500)
def internal_error(error):
	return render_template('500/index.html', error_message=str(error)), 500

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000,ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True, use_reloader=True)  # Enables HTTPS for local testing
