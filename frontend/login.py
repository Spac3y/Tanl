from flask import Blueprint, render_template, session
import google_auth_oauthlib.flow

login_bp = Blueprint('login', __name__)

@login_bp.route("/login")
def login():
	if 'credentials' in session:
		print(f"[{getCurrentTime()}]--- Logging user out ---")
	session.clear()
	return render_template("login/index.html")

@login_bp.route("/logout")
def logout():
	if 'credentials' in session:
		print(f"[{getCurrentTime()}]--- Logging user out ---")
	session.clear()
	return redirect(url_for('design'))

@login_bp.route("/google_login")
def google_login():
	session.clear()
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES
	)
	flow.redirect_uri = url_for("callback", _external=True)
	authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent', include_granted_scopes='true')
	session["state"] = state
	return redirect(authorization_url)

@login_bp.route("/callback")
def callback():
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
		CLIENT_SECRETS_FILE, scopes=SCOPES, state=session["state"]
	)
	flow.redirect_uri = url_for("callback", _external=True)

	flow.fetch_token(authorization_response=request.url)
	credentials = flow.credentials

	session["credentials"] = credentials.to_json()
	
	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	# * Save credentials to DB
	save_credentials_to_db(user_id, session['credentials'])

	return redirect(url_for("design"))
