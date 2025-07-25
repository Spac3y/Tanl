import sqlite3

def initializeUserDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	cursor.execute("""
				CREATE TABLE IF NOT EXISTS users (
				user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				sheet_id TEXT NOT NULL UNIQUE,
				whatsapp_key TEXT NOT NULL,
				whatsapp_id TEXT NOT NULL,
				email TEXT NOT NULL UNIQUE,
				credentials_json TEXT,
				last_row INTEGER NOT NULL,
				price_lead INTEGER NOT NULL DEFAULT 0,
				template_name TEXT DEFAULT 'hello_world' NOT NULL
				);
	""")
	conn.commit()
	conn.close()

def initializaEventsDB():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	cursor.execute("""
				CREATE TABLE IF NOT EXISTS message_events (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				user_id INTEGER NOT NULL,
				message_id TEXT NOT NULL UNIQUE,
				timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
				event_type TEXT CHECK(event_type IN ('sent', 'delivered' ,'read', 'responded')) NOT NULL,
				FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
				);
	""")
	conn.commit()
	conn.close()

def initializeStatusDB():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS script_status (
			user_id INTEGER PRIMARY KEY,
			status TEXT	CHECK(status IN ('stopped', 'running')) NOT NULL,
			FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
		);
		""")
		cursor.execute("""
			INSERT INTO script_status (user_id, status) values (?,?)
				 """, (1, "stopped"))
		conn.commit()
	
def addNewColumn():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("ALTER TABLE script_status ADD COLUMN timestamp DATETIME CURRENT_TIMESTAMP;")
		conn.commit()

def labamea():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE script_status SET timestamp = CURRENT_TIMESTAMP WHERE timestamp IS NULL")

def createnewtable():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("ALTER TABLE users RENAME TO users_old;")
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
				user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				sheet_id TEXT NOT NULL UNIQUE,
				whatsapp_key TEXT NOT NULL,
				whatsapp_id TEXT NOT NULL,
				email TEXT NOT NULL UNIQUE,
				credentials_json TEXT,
				last_row INTEGER NOT NULL
				);
		""") 
		cursor.execute("INSERT INTO users (user_id, sheet_id, whatsapp_key, whatsapp_id, email, credentials_json, last_row) SELECT user_id, sheet_id, whatsapp_key, whatsapp_id, email, credentials_json, last_row FROM users_old;")
		cursor.execute("DROP TABLE users_old")
# createnewtable()

def delete_script_status():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM script_status WHERE user_id = 2")
		conn.commit()