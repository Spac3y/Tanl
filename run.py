import os

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# * In-memory user cache shared across blueprints
_user_cache = {}

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.data import data_bp
from routes.webhook import webhook_bp

# * Attach shared user cache to blueprints that need it
dashboard_bp.user_cache = _user_cache
data_bp.user_cache = _user_cache

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(data_bp)
app.register_blueprint(webhook_bp)

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404/index.html', error_message=str(e)), 404

@app.errorhandler(500)
def internal_error(error):
	return render_template('500/index.html', error_message=str(error)), 500


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, ssl_context=("ssl/cert.pem", "ssl/key.pem"), debug=True, use_reloader=True)