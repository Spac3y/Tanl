from datetime import datetime

def getCurrentTime() -> str:
	now = datetime.now().strftime("%y-%m-%d %H:%M:%S")
	return now

def transformPhoneNumber(phoneNr) -> str:
	phoneNr = str(phoneNr)
	if phoneNr[0] == '7':
		return phoneNr
	phoneNumber = phoneNr
	phoneNumber = phoneNr[4:7] + phoneNr[8:11] + phoneNr[12:15]
	return phoneNumber