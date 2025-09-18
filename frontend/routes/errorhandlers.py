from flask import Flask, render_template

errorhandlers_bp = Flask(__name__)

@errorhandlers_bp.errorhandler(404)
def page_not_found(e):
	return render_template('404/index.html', error_message=str(e)), 404

@errorhandlers_bp.errorhandler(500)
def internal_error(error):
	return render_template('500/index.html', error_message=str(error)), 500
