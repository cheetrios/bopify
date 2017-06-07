"""
__name__		= bopify.py
__author__		= Cheetrios
__description__ = Main application file for deployment
"""

import uuid
import sqlite3

from flask import Flask, render_template, request, redirect
from flask import g

from forms import CreateForm

DATABASE = "db/sessions.db"

app = Flask(__name__)
app.config.from_object('config')

# ========================== DB Setup Functions ============================= #

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		g._database = sqlite3.connect(DATABASE)
		db = g._database
	return db

def create_db(cur):
	cur.execute("""CREATE TABLE sessions
       (sessid  text, sessname text, sessgenre text, 
    	masterid text, partid text)""")
	cur.commit()

def delete_db(cur):
	cur.execute("DROP TABLE sessions")
	cur.commit()

# ========================== Flask Route Setup ============================== #

@app.route("/")
def login():
	return render_template("index.html")

@app.route("/bop/<sessid>/")
def bop():
	return render_template("bop.html")

@app.route("/session/", methods=["GET", "POST"])
def session():
	cur = get_db()
	c   = cur.cursor()
	form = CreateForm()

	# case where the person just created a new session: creates a 
	# new entry in DB and redirects them to the session page
	if form.validate_on_submit():
		# print(cur.execute("""SELECT * FROM sessions 
		#	WHERE sessid = {}""".format(form.session.data)))

		session_id     = str(uuid.uuid4())  # randomly generated bop session ID
		session_name   = form.session.data  # title given to session
		session_genre  = form.genre.data    # metadata of bop session created

		master_id      = str(uuid.uuid4()) # ID of master: starts as creator
		participant_id = master_id    # ID of anyone joining: creator automatically in

		c.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", 
			[session_id, session_name, session_genre, master_id, participant_id])
		cur.commit()
		return redirect("/bop/{}/".format(session_id))

	# case of hitting the page after logging in (did not click create)
	else: 
		joinable = c.execute("""SELECT * FROM sessions""").fetchall()
		sessions = c.execute("""SELECT * FROM sessions""").fetchall()
		return render_template('session.html', 
							   joinable=joinable,
							   sessions=sessions,
							   form=form)

if __name__ == "__main__":
	app.run(host='0.0.0.0', debug=True)