
function selectTime(btn, interval) {
	document.querySelectorAll('.opt-timp').forEach(b => b.classList.remove('active'));
	btn.classList.add('active');
	console.log('Interval selectat:', interval);
}

const ctx = document.getElementById('lineChart').getContext('2d');
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
const ctx2 = document.getElementById('barChart').getContext('2d');
const chart2 = new Chart(ctx2, {
	type: 'bar',
	data: {
		labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
		datasets: [{
			label: 'Revenue',
			data: [55000, 62000, 58000, 57000, 80000, 67000, 72000, 63000, 59000, 48000, 12000, 0],
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
					callback: value => `$${value.toLocaleString()}`
				}
			}
		}
	}
});
