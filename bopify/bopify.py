"""
__name__		= bopify.py
__author__	  = Cheetrios
__description__ = Main application file for deployment
"""

import sqlite3

from flask import Flask, render_template
from flask import g

app = Flask(__name__)
DATABASE = 'db/sessions.db'

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		print(DATABASE)
		g._database = sqlite3.connect(DATABASE)
		db = g._database
	return db

@app.route("/")
def login():
	return render_template("index.html")

@app.route("/session/")
def session():
	cur = get_db().cursor()
	return render_template("session.html")

if __name__ == "__main__":
	app.run(host='0.0.0.0', debug=True)