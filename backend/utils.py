from datetime import datetime

def getCurrentTime():
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	return now