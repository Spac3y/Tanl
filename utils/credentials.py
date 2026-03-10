import google.oauth2.credentials
from google.auth.transport.requests import Request

from utils import load_credentials_from_db, save_credentials_to_db

def refresh_credentials(user_id: int):
	creds = load_credentials_from_db(user_id)
	if not creds:
		raise Exception(f"No credentials found for user: {user_id}")

	if creds.expired and creds.refresh_token:
		creds.refresh(Request())
		save_credentials_to_db(user_id, creds)

	return creds