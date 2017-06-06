"""
__name__		= bopify.py
__author__		= Cheetrios
__description__ = Main application file for deployment
"""

import sqlite3

from flask import Flask, render_template, request
from flask import g

from forms import CreateForm

DATABASE         = 'db/sessions.db'

app = Flask(__name__)
app.config.from_object('config')

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		g._database = sqlite3.connect(DATABASE)
		db = g._database
	return db

@app.route("/")
def login():
	return render_template("index.html")

@app.route("/session/", methods=["GET", "POST"])
def session():
	cur = get_db().cursor()

	# case where the person just created a new session: creates a 
	# new entry in DB and redirects them to the session page
	if request.method == 'POST':
		return render_template("bop.html")

	else: 
		form = CreateForm()
		sessions = [
			{
				"name"  : "Yash",
				"genre" : "Hip Hop"
			}, 
			{
				"name"  : "Peter",
				"genre" : "Classical"
			}, 
			{
				"name"  : "Erica",
				"genre" : "Lame"
			}, 
		]
		return render_template('session.html', 
							   sessions=sessions,
							   form=form)

@app.route("/bop/")
def bop():
	return render_template("bop.html")

if __name__ == "__main__":
	app.run(host='0.0.0.0', debug=True)