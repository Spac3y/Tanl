

// value_repsonse = document.getElementById("value_response").textContent
// seen_messages = document.getElementById("seen_messages").textContent
// respond_messages = document.getElementById("respond_messages").textContent
function updateEstimatedValue() {
	var quant = document.getElementById("value_input").value;

	if (quant === "") {
		console.log("Fill estimated value!");
	} else {
		if(Number(quant) == NaN) {
			console.log("Check value inside input!");
		} else {
			var out = document.getElementById("value_response");
			console.log(quant);
			console.log(value_response);
			out.textContent = (Number(quant) * Number(value_response));
		}
	}
}
