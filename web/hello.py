from flask import Flask

app = Flask(__name__)

@app.route("/")
def runner():
	return "<h1>Hello Worddd!</h1>"

@app.route("/dashboard")
def runcode():
	return "<h1>dashboard</h1>"