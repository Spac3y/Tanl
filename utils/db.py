import google.oauth2.credentials
import json
import sqlite3
from datetime import datetime, timedelta

def get_user_id_DB(email: str) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
		result = cursor.fetchone()
		if result:
			return result[0]
		else:
			return None

def get_len_message_sorted(user_id: int, event_type: str, timestamp: str) -> int:
	if event_type == "sent":
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
				SELECT COUNT(*) FROM message_events 
				WHERE user_id = ?
				AND timestamp > ?;
			""", (user_id, timestamp))
			count = cursor.fetchone()[0]
			return count

	elif event_type == "seen":
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

def checkAccountByEmail(email: str) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))
		exists = cursor.fetchone() is not None
		if exists:
			return True
		return False

def save_credentials_to_db(user_id: int, credentials: dict):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE users SET credentials_json = ? WHERE user_id = ?;
		""", (credentials, user_id))
		conn.commit()

def load_credentials_from_db(user_id: int):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT credentials_json FROM users WHERE user_id = ?", (user_id,))
		row = cursor.fetchone()
		if row:
			return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
		return None

def updateMessageEvent(new_type: str, message_id: str, conversation_id: str, is_response: bool, user_id: int) -> bool:
	cutoff_date = (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S")
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		if is_response and message_id == 'none':
			cursor.execute("UPDATE message_events SET event_type='responded' WHERE user_id = ? AND message_id = ? ", (user_id, conversation_id))
			conn.commit()
			return True

		if new_type == "sent":
			cursor.execute("UPDATE message_events SET message_id = ? WHERE user_id = ? AND message_id = ? AND message_id = 'none' ", (conversation_id, user_id, message_id))

		cursor.execute("UPDATE message_events SET event_type = ? WHERE user_id = ? AND message_id = ? AND timestamp > ? ",
			(new_type, user_id, message_id, cutoff_date))

		if cursor.rowcount == 0:  # * Check all messages one week old
			cursor.execute("UPDATE message_events SET event_type = ? WHERE user_id = ? AND message_id = ?",
			(new_type, user_id, message_id))
			if cursor.rowcount == 0:  # * Check all messages
				return False

		conn.commit()
		return True

def createAccount(sheet_id: str, whatsapp_key: str, whatsapp_id: str, email: str, price_lead: int, template_name: str, column_name: str, column_phone: str) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO users (sheet_id, whatsapp_key, whatsapp_id, email, last_row, price_lead, template_name, column_name, column_phone) VALUES (?,?,?,?,1,?,?,?,?)",
		(sheet_id, whatsapp_key, whatsapp_id, email, price_lead, template_name, column_name, column_phone))
		conn.commit()
		return True

def get_message_limit(user_id: int):
	try:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (user_id,))
			result = cursor.fetchall()

			if len(result) > 1:
				print(f"[{datetime.now()}][User {user_id}] ERROR!!!! - More than one user found with ID: {user_id}. Please check database for duplicates!")
				return result[0] if result else None

			if len(result) == 0:
				cursor.execute("INSERT INTO message_limit (user_id, is_on, limit_value) VALUES (?,?,?)", (user_id, 0, 100))
				conn.commit()
				cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (user_id,))
				result = cursor.fetchall()
				return result[0] if result else None

			return result[0] if result else None

	except json.JSONDecodeError:
		print(f"[{datetime.now()}][User {user_id}] Error decoding JSON data for user {user_id}")
		return None

def reset_message_limit(user_id: int, date_now: str):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE message_limit SET current_value = 0, last_day = ? WHERE user_id = ?", (date_now, user_id))
		conn.commit()
	print(f"[{datetime.now()}][User {user_id}] Message limit reset for date: {date_now}")