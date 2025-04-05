

function getTimeInterval() {
	let selectedOption = document.querySelector('input[name=monsterFeature]:checked')
	if(!selectedOption) {
		fetch('/retrieve_timeInterval', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ choice: "one_day" })
		})
			.then(response => response.json())
			.then(data => alert(data.message))
			.catch(error => console.error("ERROR: ", error))
	}
	console.log(selectedOption.id)
	fetch('/retrieve_timeInterval', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
				choice: selectedOption.id
			})
	})
	.then(response => response.json())
	.then(data => console.log("Response from FLASK: ",data))
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
		} else {
			var sent_text = document.getElementById("value_response");
			sent_text.textContent = (Number(quant) * Number(sent_mess));
			var seen_text = document.getElementById("seen_messages")
			seen_text.textContent = (Number(quant) * Number(seen_mess));
			var resp_text = document.getElementById("respond_messages");
			resp_text.textContent = (Number(quant) * Number(resp_mess));
		}
	}
}