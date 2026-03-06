from .api_routs import api_bp
from .utils import getCurrentTime

from .db.getFunctions import (
	# from backend.py
	load_credentials_from_db,
	get_user_data,
	get_message_limit,
	get_script_status,
	getPriceLead,
	# from app.py
	get_len_message_sorted,
	get_user_id_DB,
	check_if_email_exists,
)
from .db.updateFunctions import (
	# from backend.py
	createAccount,
	save_credentials_to_db,
	reset_message_limit,
	update_message_limit_current_count,
	update_message_limit,
	update_messages_table,
	update_last_line,
	# from app.py
	save_credentials_to_db,
	updateMessageEvent,
	
)