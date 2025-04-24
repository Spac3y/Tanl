
button_check_account = document.getElementById("profile-check-account")
button_save_changes = document.getElementById("profile-save")

input_email = document.getElementById("profile-email")
input_whatsapp_number = document.getElementById("profile-whatsapp-number")
input_whatsapp_token = document.getElementById("profile-whatsapp-token")
input_google_sheedID = document.getElementById("profile-google-sheetID")

window.onload(() => {
	// TODO: Check if there is user in db
	// * Insert into every field existing data
})

button_check_account.addEventListener("click", () => {

})

button_save_changes.addEventListener("click", () => {
	email = input_email.value
	whatsapp_number = input_whatsapp_number.value
	whatsapp_token = input_whatsapp_token.value
	google_sheetID = input_google_sheedID.value

	if(email.trim() === "" || whatsapp_number.trim() === "" || whatsapp_token.trim() === "" || google_sheetID.trim() === "") {
		alert("Adauga valori in toate campurile!");
		return false;
	}
})