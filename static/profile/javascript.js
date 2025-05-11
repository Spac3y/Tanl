
button_save_changes = document.getElementById("profile-save")

const input_email = document.getElementById("profile-email")
const input_whatsapp_number = document.getElementById("profile-whatsapp-number")
const input_whatsapp_token = document.getElementById("profile-whatsapp-token")
const input_google_sheedID = document.getElementById("profile-google-sheetID")
const input_price_per_lead = document.getElementById("profile-price-per-lead")

// TODO: Check if there is user in db
window.onload = (event) => {
	if (force_redirect === "1") {
		input_email.readOnly = true;
		input_email.style.backgroundColor = '#f0f0f0'; // light gray
		input_email.style.border = '1px solid gray';
		input_email.style.color = 'gray';
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
						// console.log(data)
						if(data && data.email && data.whatsapp_number && data.whatsapp_token && data.google_sheetID && data.price_lead) {
							input_email.value = data.email;
							input_whatsapp_number.value = data.whatsapp_number;
							input_whatsapp_token.value = data.whatsapp_token;
							input_google_sheedID.value = data.google_sheetID;
							input_price_per_lead.value = data.price_lead;
							console.log("INSERT current user data inside input tag");
						} else console.log("data missing from response")
					})
					.catch(error => console.error("!ERROR: ", error))
			} else {} // * Create account
		})
		.catch(error => console.log("ERROR: ", error))
	}
}

button_save_changes.addEventListener("click", () => { // * Update values account
	email = input_email
	whatsapp_number = input_whatsapp_number
	whatsapp_token = input_whatsapp_token
	google_sheetID = input_google_sheedID
	price_per_lead = input_price_per_lead

	if(email.value.trim() === "" || whatsapp_number.value.trim() === "" || whatsapp_token.value.trim() === "" || google_sheetID.value.trim() === "" || price_per_lead.value.trim() === "") {
		alert("Adauga valori in toate campurile!");
		return false;
	}
	if(force_redirect === "1") { // * Create a new account with pre-approved email
		fetch('/profile-updates', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				choice: 2,
				email: email.value,
				wNumber: whatsapp_number.value,
				wToken: whatsapp_token.value,
				gSheetID: google_sheetID.value,
				price_lead: price_per_lead.value
			})
		})
			.then(response => {response.json(); console.log(response)})
			.then(data => {
				console.log(data, data.response)
				if (data.response === 200) {
					alert("Created account successfully");
					console.log("Created new account successfully");
					window.location.href = "/";
				}
				if (data.response === 500) {
					alert("Error creating account inside db - Internal Server Error");
					console.error("Internal server errror");
				}
			})
			.catch(error => console.log("ERROR: ", error))
	} else {
		fetch('/profile-updates', {
			method: 'POST',
			headers: { 'Content-Type' : 'application/json' },
			body: JSON.stringify({
				choice : 1,
				email: email.value,
				wNumber: whatsapp_number.value,
				wToken: whatsapp_token.value,
				gSheetID: google_sheetID.value,
				price_lead: price_per_lead.value
			})
		})
		.then(response => response.json())
		.then(data => {
			console.log(data, data.response)
			if(data.response === 200 || data['result'] === "success") {
				console.log("Updated account details successfully");
				window.location.href = "/";
			}
			if (data.response === 500 || data['result'] !== "success") {
				alert("Error updating values inside db - Internal Server Error");
				console.error("Internal server errror");
			}
		})
		.catch(error => console.log("ERROR: ", error))
	}
})