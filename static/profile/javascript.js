
button_check_account = document.getElementById("profile-check-account")
button_save_changes = document.getElementById("profile-save")

input_email = document.getElementById("profile-email")
input_whatsapp_number = document.getElementById("profile-whatsapp-number")
input_whatsapp_token = document.getElementById("profile-whatsapp-token")
input_google_sheedID = document.getElementById("profile-google-sheetID")

// TODO: Check if there is user in db
window.onload = (event) => {
	if (force_redirect === "1") {
		console.log("Force redirect!");
		alert("Account was not found in DB. Please create one!");
		input_email.value = email;
	} else {
		console.log("Not force redirect!");
		vEmail =  email;

		fetch('/profile-updates', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				email: vEmail,
				choice: 0
			})
		}).then(response => response.json())
		.then( data => {
			if(data.result === 'true') { // * The account is found in db
				fetch('/profile-updates').then(response => response.json())
					.then(data => {
						if(data && data.email && data.whatsapp_number && data.whatsapp_token && data.google_sheetID) {
							input_email.value = data.email;
							input_whatsapp_number.value = data.whatsapp_number;
							input_whatsapp_token.value = data.whatsapp_token;
							input_google_sheedID.value = data.google_sheetID;
							// console.log("INSERT current user data inside input tag");
						} else console.log("data missing from response")
					})
					.catch(error => console.error("!ERROR: ", error))
			} else {} // * Create account
		})
		.catch(error => console.log("ERROR: ", error))
	}
}

button_check_account.addEventListener("click", () => {
	email = input_email.value;
	fetch('/profile-updates', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			email : email,
			choice: 0
		})
	}).then(response => response.json())
	.then(data => {
		status_indicator = document.getElementById('email-status')
		if(data.result === "true") {
			status_indicator.textContent = "Found";
			status_indicator.style.color = "green";
		} else {
			status_indicator.textContent = "Not found";
			status_indicator.style.color = "red";
		}
	})
	.catch(error => console.error("!ERROR: ", error))
})

button_save_changes.addEventListener("click", () => { // * Update values account
	email = input_email
	whatsapp_number = input_whatsapp_number
	whatsapp_token = input_whatsapp_token
	google_sheetID = input_google_sheedID

	if(email.value.trim() === "" || whatsapp_number.value.trim() === "" || whatsapp_token.value.trim() === "" || google_sheetID.value.trim() === "") {
		alert("Adauga valori in toate campurile!");
		return false;
	}
	fetch('/profile-updates', {
		method: 'POST',
		headers: { 'Content-Type' : 'application/json' },
		body: JSON.stringify({
			choice : 1,
			email: email.value,
			wNumber: whatsapp_number.value,
			wToken: whatsapp_token.value,
			gSheetID: google_sheetID.value
		})
	})
	.then(response => response.json())
	.then(data => {
		console.log(data, data.response)
		if(data.response === 200) console.log("Updated account details successfully");
		if(data.response === 500) {
			alert("Error updating values inside db - Internal Server Error");
			console.error("Internal server errror");
		}

	})
	.catch(error => console.log("ERROR: ", error))
})