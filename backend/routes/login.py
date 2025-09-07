from flask import Blueprint, render_template, session

login_bp = Blueprint('login', __name__)

@login_bp
def login():
	if 'credentials' in session:
		print(f"[{getCurrentTime()}]--- Logging user out ---")
	session.clear()
	return render_template("login/index.html")