import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")
APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
RECEIVER_EMAIL = "email@email.com"

subject = "Client nou interesat de produs!!"
email_message = MIMEMultipart()
email_message['From'] = SENDER_EMAIL
email_message['To'] = RECEIVER_EMAIL
email_message['Subject'] = subject


def handlePreconfResponse(data):
	# * Check for preconfigured response
	try:
		messages = data['entry'][0]['changes'][0]['value']['messages']
		# * Check if message is preconfigured button message
		if not messages:
			return "No messages", 200

		msg = messages[0]
		if msg['type'] != 'button':
			return "Ignored: Not a button", 200

		button_message = msg['button']['payload']
		phone = msg['from']

		print("------------------------")
		print(phone, button_message, type(button_message))

		# * Send email with the button message and phone number
		try:
			body = str(phone) + " | " + button_message
			email_message.attach(MIMEText(body, 'plain'))
			with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
				server.login(SENDER_EMAIL, APP_PASSWORD)
				server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_message.as_string())
				print("✅ Email sent successfully!")
		except Exception as e:
			print("Error:", e)

		return "Button processed", 200

	except Exception as e:
		return f"Error: {str(e)}", 400