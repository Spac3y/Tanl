from flask import Blueprint, jsonify, request, session

from backend import utils
from utils.charts import calculate_date_range, getCustomValues, getMonthlyValues
from utils.db import get_len_message_sorted
from utils.user_helpers import getUserID, retUser

data_bp = Blueprint('data', __name__)


# *
@data_bp.route('/submit_json', methods=['POST'])
def submit_json():
	data = request.get_json()
	if not data or "choice" not in data:
		return jsonify({"error": "Invalid request"}), 400

	if 'credentials' not in session:
		from flask import redirect, url_for
		return redirect(url_for('auth.login'))

	user_id = getUserID()
	received_data = data['choice']
	time_interval = calculate_date_range(received_data)
	sent_count = get_len_message_sorted(user_id[1], 'sent', time_interval)
	seen_count = get_len_message_sorted(user_id[1], 'seen', time_interval)
	resp_count = get_len_message_sorted(user_id[1], 'responded', time_interval)
	price_lead = retUser(user_id[1], data_bp.user_cache).getPriceLead()
	monthly_values = getMonthlyValues(user_id[1])
	custom_values = getCustomValues(received_data, user_id[1])

	return jsonify({
		"sent_count": sent_count,
		"seen_count": seen_count,
		"resp_count": resp_count,
		"price-lead": price_lead,
		"monthly_values": monthly_values,
		"custom_values": custom_values,
		"result": "succes"
	})


# *
@data_bp.route('/status', methods=['POST'])
def status():
	user_id = getUserID()[1]
	ps = retUser(user_id, data_bp.user_cache).get_script_status()
	thread_status = retUser(user_id, data_bp.user_cache).is_thread_running()
	value = None

	if thread_status and ps:
		value = "Running"
	elif ps and not thread_status:
		value = "Stopped"
		retUser(user_id, data_bp.user_cache).update_script_status("stopped")
	elif not ps and thread_status:
		value = "Running"
		retUser(user_id, data_bp.user_cache).update_script_status("running")
	elif not ps and not thread_status:
		value = "Stopped"
	else:
		value = "Error"

	return jsonify({'status': value})


# *
@data_bp.route('/start-stop', methods=['POST'])
def start_stop():
	data = request.get_json()
	if not data or "choice" not in data or 'credentials' not in session:
		return jsonify({"error": "Invalid request"}), 400

	received_data = data['choice']
	user_id = getUserID()[1]

	if received_data == '0':
		retUser(user_id, data_bp.user_cache).stop_listener()
		return jsonify({"message": "Stopped script"}), 200

	elif received_data == '1':
		print(f"[{utils.getCurrentTime()}][User {user_id}] Starting script")
		retUser(user_id, data_bp.user_cache).launch_listener()
		return jsonify({"message": "Started script"}), 200

	print(f"[{utils.getCurrentTime()}][User {user_id}] Error invalid value provided")
	return jsonify({"error": "Invalid value provided"}), 400