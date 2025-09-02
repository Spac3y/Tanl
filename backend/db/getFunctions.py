import sqlite3
import google.oauth2.credentials

# TODO: getters - Implement test functions for each of these functions 

# All getter functions will get try/ expect for missign data case
# --- backend.py ---

def load_credentials_from_db(user_id : int):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT credentials_json FROM users WHERE user_id = ?", (user_id, ))
		row = cursor.fetchone()
		if row[0] is not None:
			return google.oauth2.credentials.Credentials.from_authorized_user_info(json.loads(row[0]))
		return None

def get_user_data(user_id: int):
	try:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE user_id = ?" , (user_id,))
			result =  cursor.fetchall()

			if len(result) > 1:
				print(f"[{getCurrentTime()}][User {user_id}] ERROR!!! - More than one user found with ID: {user_id}. Please check database for duplicates!")
			
			return result[0] if result else None
	except json.JSONDecodeError:
		print(f"[{getCurrentTime()}][User {user_id}] Error decoding JSON data for user {user_id}")
		return None

def get_message_limit(user_id:int):
	try:
		with sqlite3.connect("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (user_id,))
			result = cursor.fetchall()

			if len(result) > 1:
				print(f"[{getCurrentTime()}][User {user_id}] ERROR!!!! - More than one user found with ID: {user_id}. Please check database for duplicates!")
				return result[0] if result else None
			
			if len(result) == 0:
				cursor.execute("INSERT INTO message_limit (user_id, is_on, limit_value) VALUES (?,?,?)", (user_id, 0, 100))
				conn.commit()
				cursor.execute("SELECT * FROM message_limit WHERE user_id = ?", (user_id,))
				result = cursor.fetchall()
				return result[0] if result else None
			
			return result[0] if result else None
	
	except json.JSONDecodeError:
		print(f"[{getCurrentTime()}][User {user_id}] Error decoding JSON data for user {user_id}")
		return None

def get_script_status(user_id: int) -> bool:
	with sqlite3.connect('database.db') as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT status FROM script_status WHERE user_id = ?", (user_id,))
		result = cursor.fetchone()
		if result:
			status = result[0]
			if status == 'running': return True
			elif status == 'stopped': return False
		else:
			cursor.execute("INSERT INTO script_status (user_id, status) VALUES (?, ?)", (user_id, "stopped"))
			conn.commit()
			return False
		
		raise ValueError(f"Either no value was found for USER_ID: {user_id} OR bad value from status_script: {result}")

def getPriceLead(user_id: int) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT price_lead FROM users WHERE user_id = ?", (user_id,))
		result = cursor.fetchone()[0]
		return result

# --- END backend.py ---

# --- app.py ---
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

def get_user_id_DB(email:str) -> int:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
		result = cursor.fetchone()
		if result:
			return result[0]
		else:
			return None

def checkAccountByEmail(email: str) -> bool:
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))
		exists = cursor.fetchone() is not None

		if exists: return True
		return False