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
				template_name TEXT DEFAULT 'hello_world' NOT NULL,
				column_name TEXT DEFAULT 'A' NOT NULL,
				column_phone TEXT DEFAULT 'B' NOT NULL
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
			status TEXT	CHECK(status IN ('stopped', 'running')) NOT NULL DEFAULT 'stopped',
			FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
		);
		""")
		conn.commit()

def initializeMessageLimitDB():
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS message_limit (
			user_id INTEGER PRIMARY KEY,
			is_on BOOLEAN NOT NULL DEFAULT 0,
			limit_value INTEGER NOT NULL DEFAULT 1000,
			current_value INTEGER NOT NULL DEFAULT 0,
			last_day TEXT NOT NULL DEFAULT (DATE('now')),
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
			);
		""")
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

def delete_script_status(user_id):
	with sqlite3.connect("database.db") as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM script_status WHERE user_id = ?", (user_id,))
		conn.commit()

if __name__ == "__main__":
	# initializeUserDB()
	# initializaEventsDB()
	# initializeStatusDB()
	initializeMessageLimitDB()
	# addNewColumn()
	# labamea()
	print("Database initialized successfully.")