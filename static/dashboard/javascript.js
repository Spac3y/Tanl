
start_button = document.getElementById('start')
stop_button = document.getElementById('stop')


window.onload = function () {
	console.log("window on log functino called")
	fetch('/status', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({status: '0'})
	})
	.then(response => response.json())
	.then(data => {
		console.log("Response from Flask:", data.status)
		document.getElementById("text_status").textContent = data.status
		if (data.status == "Running") document.getElementById("text_status").style.color = "green"
		else document.getElementById("text_status").style.color = "red"
	})
	.catch(error => console.log("ERROR: ", error))
}

start_button.addEventListener("click", () => {
	fetch('/start-stop', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ choice: "1" })
	})
	.then(response => response.json())
	.then(data => {
		alert(data.message)
		p = document.getElementById("text_status")
		p.textContent = "Running"
		p.style.color = "green"
	})
	.catch(error => console.error("ERROR: ", error))
})

stop_button.addEventListener("click", () => {
	fetch('/start-stop', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ choice : "0" })
	})
	.then(response => response.json())
	.then(data => {
		alert(data.message)
		p = document.getElementById("text_status")
		p.textContent = "Stopped"
		p.style.color = "red"
	})
	.catch(error => console.error("ERROR: ", error))
})

function getTimeInterval() {
	let selectedOption = document.querySelector('input[name=monsterFeature]:checked')
	if(!selectedOption) {
		fetch('/submit_json', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ choice: "one_day" })
		})
			.then(response => response.json())
			.then(data => alert(data.message))
			.catch(error => console.error("ERROR: ", error))
	}
	console.log(selectedOption.id)
	fetch('/submit_json', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
				choice: selectedOption.id
			})
	})
	.then(response => response.json())
	.then(data => {
		var quant = document.getElementById("value_input").value;

		if (quant === "") {
			alert("Introdu Valoarea aproximativa a unui lead");
		} else {
			var sent_text = document.getElementById("value_response");
			sent_text.textContent = (Number(quant) * Number(data['sent_count']));
			var seen_text = document.getElementById("seen_messages")
			seen_text.textContent = (Number(data['seen_count']));
			var resp_text = document.getElementById("respond_messages");
			resp_text.textContent = (Number(data['resp_count']));
		}
	})
	.catch(error => console.error("ERROR: ", error))
}

function updateEstimatedValue() {
	getTimeInterval()
	var quant = document.getElementById("value_input").value;

	if (quant === "") {
		alert("Introdu Valoarea aproximativa a unui lead");
	} else {
		if(Number(quant) == NaN) {
			console.log("Verifica daca valoarea introdusa este un numar!");
		}
	// 	else {
		// 	var sent_text = document.getElementById("value_response");
		// 	sent_text.textContent = (Number(quant) * Number(sent_mess));
		// 	var seen_text = document.getElementById("seen_messages")
		// 	seen_text.textContent = (Number(quant) * Number(seen_mess));
		// 	var resp_text = document.getElementById("respond_messages");
		// 	resp_text.textContent = (Number(quant) * Number(resp_mess));
		// }
	}
}