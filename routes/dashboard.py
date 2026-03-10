from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from utils import getCurrentTime, getEmail, getUserID, retUser, checkAccountByEmail, get_user_id_DB, createAccount

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def design():
	if 'credentials' not in session:
		return redirect(url_for('auth.login'))

	user_id = getUserID()

	if getUserID()[0] == -1:
		return redirect(url_for('dashboard.profile', force_redirect=1, email=user_id[1]))

	user = retUser(user_id[1], dashboard_bp.user_cache)
	script_status = user.get_script_status()
	return render_template("design/index.html", script_st=script_status), 200


@dashboard_bp.route("/user_info")
def read_sheet():
	if 'credentials' not in session:
		return redirect(url_for('auth.login'))

	user_id = getUserID()

	if getUserID()[0] == -1:
		return redirect(url_for('dashboard.profile', force_redirect=1, email=user_id[1]))

	user = retUser(user_id[1], dashboard_bp.user_cache)
	script_status = user.get_script_status()
	print(f"[{getCurrentTime()}][User {user_id[1]}] Script is running") if script_status else print(f"[{getCurrentTime()}][User {getUserID()[1]}] Script is stopped")

	return render_template("dashboard/index.html", script_st=script_status)


# TODO: When creating account put email inside cookie not url
@dashboard_bp.route("/profile")
def profile():
	force_redirect = request.args.get('force_redirect', default=0, type=int)
	email = request.args.get('email', default=getEmail(), type=str)
	return render_template('profile/index.html', force_redir=force_redirect, email=email)


# *
@dashboard_bp.route("/profile-updates", methods=['GET', 'POST'])
def profile_updates():
	if 'credentials' not in session:
		return jsonify({"result" : "credentials not in session"}), 401 
	else:
		if request.method == 'GET':
			user_data = retUser(getUserID()[1], dashboard_bp.user_cache).get_user_data()
			message_limit = retUser(getUserID()[1], dashboard_bp.user_cache).get_message_limit()
			response = {
				"email": user_data[4],
				"whatsapp_number": user_data[3],
				"whatsapp_token": user_data[2],
				"google_sheetID": user_data[1],
				"price_lead": user_data[7],
				"template_name": user_data[8],
				"column_name": user_data[9],
				"column_phone": user_data[10],
				"limit_enabled": message_limit[1],
				"message_limit": message_limit[2]
			}
			return jsonify(response), 200

		elif request.method == 'POST':
			data = request.get_json()
			if data['choice'] == 0:  # * choice = 0 -> Check for email in db
				received_data = data['email']
				result = None
				if checkAccountByEmail(received_data):
					result = "true"
				else:
					result = "false"
				return jsonify({"result": result}), 200

			elif data['choice'] == 1:  # * choice = 1 -> Update values for user
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

				if checkAccountByEmail(vEmail) == True:  # * Account exists, update current values
					current_user = retUser(get_user_id_DB(vEmail), dashboard_bp.user_cache)
					if current_user.update_account_details(vEmail, vWNumber, vWToken, vGSheetID, vPriceLead, vTemplateName, vNameCol, vPhoneCol) and current_user.update_message_limit(limitEnabled, mLimit):
						current_user.refresh()
						return jsonify({"result": "success"}), 200
					else:
						return jsonify({"result": "error"}), 500
				else:  # * Create new account
					print("Account not found")
					return jsonify({"result": "not_found"}), 404

			elif data['choice'] == 2:  # * choice = 2 -> Create a new account for accepted user
				vEmail = data['email']
				vWToken = data['wToken']
				vWNumber = data['wNumber']
				vGSheetID = data['gSheetID']
				vPriceLead = data['price_lead']
				vTemplateName = data['tName']
				vNameCol = data['cName']
				vPhoneCol = data['cPhone']
				if createAccount(vGSheetID, vWToken, vWNumber, vEmail, vPriceLead):
					return jsonify({"result": "success"}), 200
				return jsonify({"result": "false"}), 500
		else:
			return "Method not allowed", 405