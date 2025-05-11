

start_button = document.getElementById('start')
stop_button = document.getElementById('stop')

const ctx = document.getElementById('lineChart').getContext('2d');
const ctx2 = document.getElementById('barChart').getContext('2d');

const defaultTimeInterval = "one_year"

window.onload = function () {
	getTimeInterval(defaultTimeInterval)
	console.log("window on log functino called")
	fetch('/status', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ status: '0' })
	})
		.then(response => response.json())
		.then(data => {
			console.log("Response from Flask:", data.result)
			document.getElementById("text_status").textContent = data.status
			if (data.status == "Running") document.getElementById("text_status").style.color = "green"
			else document.getElementById("text_status").style.color = "red"
		})
		.catch(error => console.log("ERROR: ", error))
}

function selectTime(btn, interval) {
	document.querySelectorAll('.opt-timp').forEach(b => b.classList.remove('active'));
	btn.classList.add('active');
	getTimeInterval(interval)
	console.log('Interval selectat:', interval);
}

function getTimeInterval(selectedInterval) {
	if (!selectedInterval) {
		selectedInterval = "one_day";
	}
	fetch('/submit_json', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			choice: selectedInterval
		})
	})
		.then(response => response.json())
		.then(data => {
			console.log(data);
			quant = Number(data['price-lead'])

			if (quant === "") {
				alert("Eroare Interna: Nu se poate preluare valoare / raspuns din DB");
			} else {
				var sent_text = document.getElementById("price-per-lead-value");
				sent_text.textContent = (Number(quant) * Number(data['sent_count']));
				var seen_text = document.getElementById("seen-messages-value")
				seen_text.textContent = (Number(data['seen_count']));
				var resp_text = document.getElementById("responded-messages-value");
				resp_text.textContent = (Number(data['resp_count']));
				var sent_text_count = document.getElementById("sent-messages-value");
				sent_text_count.textContent = (Number(data['sent_count']));
				for(let i = 0; i<12;i++) {
					let value = data['monthly_values'][i] * quant;
					console.log(value);
					chart2.data.datasets[0].data[i] = value;
				}
				chart2.update();
			}
		})
		.catch(error => console.error("ERROR: ", error))
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
		body: JSON.stringify({ choice: "0" })
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

const chart = new Chart(ctx, {
	type: 'line',
	data: {
		labels: ['23 Nov', '24', '25', '26', '27', '28', '29', '31'],
		datasets: [{
			label: 'Revenue',
			data: [23000, 25000, 30000, 35000, 37000, 41000, 39000, 47000],
			borderColor: '#89502d',
			backgroundColor: 'rgba(0, 0, 0, 0.1)',
			pointBackgroundColor: '#c3713e',
			pointBorderColor: '#c3713e',
			pointBorderWidth: 2,
			pointRadius: function (context) {
				return context.dataIndex === context.dataset.data.length - 1 ? 6 : 4;
			},
			tension: 0.2
		}]
	},
	options: {
		responsive: true,
		plugins: {
			legend: {
				display: false
			},
			tooltip: {
				mode: 'index',
				intersect: false,
			}
		},
		scales: {
			y: {
				beginAtZero: false,
				ticks: {
					callback: value => `$${value.toLocaleString()}`
				}
			}
		}
	}
});

const chart2 = new Chart(ctx2, {
	type: 'bar',
	data: {
		labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
		datasets: [{
			label: 'Revenue',
			data: [0,0,0,0,0,0,0,0,0,0,0,0],
			backgroundColor: '#c3713e',
			borderRadius: 3, // Optional: rounded bar corners
			barThickness: 15
		}]
	},
	options: {
		responsive: true,
		plugins: {
			legend: { display: false }
		},
		scales: {
			y: {
				beginAtZero: true,
				ticks: {
					callback: value => `${value.toLocaleString()}RON`
				}
			}
		}
	}
});
