import json
import sqlite3

# All update functions 
# TODO: updaters - Implement test functions for each of these functions 

# --- backend.py ---

def createAccount(sheet_id: str, whatsapp_key: str, whatsapp_id:str, email: str, price_lead:int, template_name: str, column_name:str, column_phone:str ) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor .execute("INSERT INTO users (sheet_id, whatsapp_key, whatsapp_id, email, last_row, price_lead, template_name, column_name, column_phone) VALUES (?,?,?,?,1,?,?,?,?)",
		(sheet_id, whatsapp_key, whatsapp_id, email, price_lead))
		conn.commit()
		return True

def save_credentials_to_db(self, user_id : int, credentials : dict):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE users SET credentials_json = ? WHERE user_id = ?;
		""", (credentials.to_json(), user_id))
		conn.commit()

def reset_message_limit(self, date_now: str):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE message_limit SET current_value = 0, last_day = ? WHERE user_id = ?", (date_now, self.user_id))
		conn.commit()
	print(f"[{getCurrentTime()}][User {self.user_id}] Message limit reset for date: {date_now}")

def update_message_limit_current_count(self):
	try:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
			UPDATE message_limit SET current_count = current_count + 1 WHERE user_id = ?;
			""", (self.user_id,))
			conn.commit()
			return True
	except sqlite3.Error as e:
		print(f"[{getCurrentTime()}][User {self.user_id}] Error updating message count: {e}")
		return False

def update_message_limit(self, is_on: bool, value: int):
	try:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("""
			INSERT INTO message_limit (user_id, is_on, limit_value)
			VALUES (?, ?, ?)
			ON CONFLICT(user_id) DO UPDATE SET
				is_on = excluded.is_on,
				limit_value = excluded.limit_value;
			""", (self.user_id, is_on, value))
			conn.commit()
			return True

def update_messages_table(self, message_id, conversation_id, event_type):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			INSERT INTO message_events (user_id, message_id, event_type) VALUES (?,?,?,?)
		""", (self.user_id, message_id, event_type))
		conn.commit()

			def update_account_details(self, email: str, wNumber: str, wToken: str, gSheetID: str, price_lead: int, template_name: str, name_col: str, phone_col: str) -> bool:
	name_col = name_col.upper()
	phone_col = phone_col.upper()

	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE users SET email = ?, whatsapp_key = ?, whatsapp_id = ?, sheet_id = ?, price_lead = ?, template_name = ?, column_name = ?, column_phone = ? WHERE user_id = ?", (email, wToken, wNumber, gSheetID, price_lead, template_name,name_col, phone_col, self.user_id))
		conn.commit()
	return True

def update_last_line(self, last_row):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE users SET last_row = ? WHERE user_id = ?", (last_row, self.user_id))
		conn.commit()

def update_script_status(self, status):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			INSERT INTO script_status (user_id, status) VALUES (?,?) ON CONFLICT (user_id) DO UPDATE SET status = excluded.status
		""", (self.user_id, status))
		conn.commit()

# --- END backend.py ---

# --- app.py ---
def save_credentials_to_db(user_id : int, credentials : dict):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			UPDATE users SET credentials_json = ? WHERE user_id = ?;
		""", (credentials, user_id))
		conn.commit()

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