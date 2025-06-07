import os
import subprocess
from time import sleep
import json
import sqlite3
from flask import Flask, redirect, request, session, url_for, render_template, jsonify

VERIFY_TOKEN = "my_super_secret_token"
app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
	if request.method == 'GET':
		mode = request.args.get('hub.mode')
		token = request.args.get('hub.verify_token')
		challenge = request.args.get('hub.challenge')

		if mode == 'subscribe' and token == VERIFY_TOKEN:
			print("Webhook verified successfully!")
			return challenge, 200
		else:
			print("Webhook verification failed.")
			return "Not found", 404

	elif request.method == 'POST':
		# TODO: Find the message to change status ( search max 1 week old) ignore if status from webhook is sent
		data = request.json
		conversation_id =  data['entry'][0]['id']
		is_response = False

		if 'contacts' in data['entry'][0]['changes'][0] and 'messages' in data['entry'][0]['changes'][0]:
			is_response = True
			message_id = 'none'
		else:
			status = data['entry'][0]['changes'][0]['value']['statuses'][0]['status']
			message_id = data['entry'][0]['changes'][0]['value']['statuses'][0]['id']

		
		return jsonify({"error" : "Internal server error"}), 500

if __name__ == "__main__":
	app.run(debug=True)