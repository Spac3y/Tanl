import sqlite3
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta


def calculate_date_range(subtraction_value: str):
	now = datetime.now()

	cases = {
		"one_day": now - timedelta(days=1),
		"two_day": now - timedelta(days=2),
		"three_day": now - timedelta(days=3),
		"five_day": now - timedelta(days=5),
		"one_week": now - timedelta(weeks=1),
		"two_week": now - timedelta(weeks=2),
		"one_month": now - relativedelta(months=1),
		"six_month": now - relativedelta(months=6),
		"one_year": now - relativedelta(years=1)
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
		bucket_count = 10
		bucket_size = total_hours // bucket_count

		start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=total_hours)

		for i in range(bucket_count):
			bucket_start = start_time + timedelta(hours=i * bucket_size)
			bucket_end = bucket_start + timedelta(hours=bucket_size)

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