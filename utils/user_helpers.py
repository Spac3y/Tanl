import json

import google.auth.exceptions
import google.oauth2.credentials
from flask import redirect, session, url_for
from googleapiclient.discovery import build

from backend import utils
from utils import get_user_id_DB


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
		print(f"[{utils.getCurrentTime()}] Error refreshing credentials: {e}")
		return redirect(url_for('login'))


def getUserID():
	email = getEmail()
	user_id = get_user_id_DB(email)
	if user_id is not None:
		return [1, user_id]
	else:
		print(f"[{email}]User not found in DB but email is accepted | Redirect -> Create account")
		return [-1, email]


def retUser(user_id: int, _user_cache: dict):
	from backend import User
	if user_id not in _user_cache:
		_user_cache[user_id] = User(user_id)
	return _user_cache[user_id]