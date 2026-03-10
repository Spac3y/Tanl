import os

from flask import Blueprint, jsonify, request

from utils import getUserID, handlePreconfResponse, updateMessageEvent

webhook_bp = Blueprint('webhook', __name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
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
		data = request.json
		conversation_id = data['entry'][0]['id']
		is_response = False

		if 'contacts' in data['entry'][0]['changes'][0] and 'messages' in data['entry'][0]['changes'][0]:
			is_response = True
			message_id = 'none'
			# * will be used later when implementing whatsapp client side
			# message_id = data['entry'][0]['changes'][0]['value']['messages'][0]['id']
			# client_name = data['entry'][0]['changes'][0]['value']['contacts'][0]['profile']['name']
			# client_phone = data['entry'][0]['changes'][0]['value']['contacts'][0]['wa_id']
		else:
			status = data['entry'][0]['changes'][0]['value']['statuses'][0]['status']
			message_id = data['entry'][0]['changes'][0]['value']['statuses'][0]['id']

		if updateMessageEvent(status, message_id, conversation_id, is_response, getUserID()[1]) == True:
			return jsonify({"status": "success"}), 200
		return jsonify({"error": "Internal server error"}), 500

		# BUG: unreachable code — kept as-is per request
		handlePreconfResponse()