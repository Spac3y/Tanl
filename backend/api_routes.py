from flask import Flask

@app.route('/submit_json', methods=['POST'])
def submit_json():
	data = request.get_json()
	if not data or "choice" not in data:
		return jsonify({"error" : "Invalid request"}), 400
	# print("[ JSON Received from js Code ] : ", data['choice'])

	if 'credentials' not in session:
		return redirect(url_for('index'))
	credentials_info = json.loads(session['credentials'])
	credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(info=credentials_info)

	# * Get the users email
	service = build('people', 'v1', credentials=credentials)
	profile = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
	email = profile.get('emailAddresses', [])[0].get('value')
	user_id = get_user_id_DB(email)

	received_data = data['choice']
	time_interval = calculate_date_range(received_data)
	sent_count = get_len_message_sorted(user_id, 'sent', time_interval)
	seen_count = get_len_message_sorted(user_id, 'seen', time_interval)
	resp_count = get_len_message_sorted(user_id, 'responded', time_interval)
	price_lead = retUser(getUserID()[1]).getPriceLead()
	monthly_values = getMonthlyValues(user_id)
	custom_values = getCustomValues(received_data,user_id)

	return jsonify( {
		"sent_count" : sent_count,
		"seen_count" : seen_count,
		"resp_count" : resp_count,
		"price-lead" : price_lead,
		"monthly_values" : monthly_values,
		"custom_values" : custom_values,
		"result" : "succes"
	})

@app.route('/status', methods=['POST'])
def status():
	ps = retUser(getUserID()[1]).get_script_status()
	thread_status = retUser(getUserID()[1]).is_thread_running()
	value = None

	if thread_status and ps:
		value = "Running"
	elif ps and not thread_status:
		value = "Stopped"
		retUser(getUserID()[1]).update_script_status("stopped")
	elif not ps and thread_status:
		value = "Running"
		retUser(getUserID()[1]).update_script_status("running")
	elif not ps and not thread_status:
		value = "Stopped"
	else:
		value = "Error"

	return jsonify({'status' : value })

@app.route("/profile-updates", methods=['GET', 'POST'])
def profile_updates():
	if 'credentials' not in session:
		return 401
	else:
		if request.method == 'GET':
			user_data = retUser(getUserID()[1]).get_user_data()
			message_limit = retUser(getUserID()[1]).get_message_limit()
			response = {
				"email": user_data[4],
				"whatsapp_number": user_data[3],
				"whatsapp_token": user_data[2],
				"google_sheetID": user_data[1],
				"price_lead": user_data[7],
				"template_name" : user_data[8],
				"column_name" : user_data[9],
				"column_phone" : user_data[10],
				"limit_enabled" : message_limit[1],
				"message_limit" : message_limit[2]
			}
			return jsonify(response), 200
		elif request.method == 'POST':
			data = request.get_json()
			if data['choice'] == 0: # * choice = 0 -> Check for email in db
				received_data = data['email']
				result = None
				if(checkAccountByEmail(received_data)): 
					result = "true"
				else: 
					result = "false"
				return jsonify({"result": result}), 200
			elif data['choice'] == 1: # * choice = 1 -> Update values for user
				vEmail = data['email']
				vWToken = data['wToken']
				vWNumber = data['wNumber']
				vGSheetID = data['gSheetID']
				vPriceLead = data['price_lead']
				vTemplateName = data['tName']
				vNameCol = data['cName']
				vPhoneCol = data['cPhone']
				limitEnabled = data['limitEnabled']
				mLimit = data['mLimit']

				if(checkAccountByEmail(vEmail) == True): # * Account exists, update current values
					current_user = retUser(get_user_id_DB(vEmail))
					if(current_user.update_account_details(vEmail, vWNumber, vWToken, vGSheetID, vPriceLead, vTemplateName, vNameCol, vPhoneCol) and current_user.update_message_limit(limitEnabled, mLimit)):
						current_user.refresh()
						return jsonify({ "result" : "success" }), 200
					else: 
						return jsonify({"result" : "error"}), 500
				else: # * Create new account
					print("Account not found")
					return jsonify({"result" : "not_found"}), 404
				
			elif data['choice'] == 2: # * choice = 2 -> Create a new account for accepted user
				vEmail = data['email']
				vWToken = data['wToken']
				vWNumber = data['wNumber']
				vGSheetID = data['gSheetID']
				vPriceLead = data['price_lead']
				vTemplateName = data['tName']
				vNameCol = data['cName']
				vPhoneCol = data['cPhone']
				if(createAccount(vGSheetID, vWToken, vWNumber, vEmail, vPriceLead)): # * accout created in db
					return jsonify({ "result" : "success"}), 200
				return jsonify({ "result" : "false"}), 500
		else:
			return "Method not allowed",405

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
		data = request.json
		conversation_id =  data['entry'][0]['id']
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
		
		if(updateMessageEvent(status, message_id, conversation_id, is_response,  getUserID[1]) == True):
			return jsonify({"status" : "success"}), 200
		return jsonify({"error" : "Internal server error"}), 500

		handlePreconfReponse()
