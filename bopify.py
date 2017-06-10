"""
__name__		= bopify.py
__author__		= Cheetrios
__description__ = Main application file for deployment
"""

import uuid
import sqlite3

import spotipy
import spotipy.util as util

from flask import Flask, render_template, request, redirect, url_for, session
from flask_oauthlib.client import OAuth, OAuthException
from flask import g

from forms import CreateForm, JoinForm

DATABASE = "db/sessions.db"

SPOTIFY_APP_ID	 = "d251ae2dd5824052874019013ee73eb0"
SPOTIFY_APP_SECRET = "ee5c56305aea428b986c4a0964361cb2"

app = Flask(__name__)
app.config.from_object("config")

oauth = OAuth(app)

# ========================== Spotify Authenticate ============================ #

spotify = oauth.remote_app(
	"spotify",
	consumer_key=SPOTIFY_APP_ID,
	consumer_secret=SPOTIFY_APP_SECRET,
	# Change the scope to match whatever it us you need
	# list of scopes can be found in the url below
	# https://developer.spotify.com/web-api/using-scopes/
	request_token_params={"scope": "user-read-email"},
	base_url="https://accounts.spotify.com",
	request_token_url=None,
	access_token_url="/api/token",
	authorize_url="https://accounts.spotify.com/authorize"
)

@spotify.tokengetter
def get_spotify_oauth_token():
	return session.get("oauth_token")

# ========================== DB Setup Functions ============================= #

def get_db():
	db = getattr(g, "_database", None)
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
def index():
	return redirect(url_for("login"))
	#return render_template("index.html")

@app.route("/login/")
def login():
	callback = url_for(
		"spotify_authorized",
		next=request.args.get("next") or request.referrer or None,
		_external=True
	)
	return spotify.authorize(callback=callback)

@app.route("/login/authorized/")
def spotify_authorized():
	resp = spotify.authorized_response()

	# used to confirm that a user has logged in (for finding sessions)
	session['user_id'] = spotify.consumer_secret
	return redirect(url_for("bop"))

@app.route("/room/<sessid>/")
def room(sessid):
	return render_template("bop.html")

@app.route("/bop/", methods=["GET", "POST"])
def bop():
	print(session['user_id'])

	cur = get_db()
	c   = cur.cursor()
	
	create = CreateForm()
	join   = JoinForm()

	# case where the person just created a new session: creates a 
	# new entry in DB and redirects them to the session page
	if create.validate_on_submit():
		# print(cur.execute("""SELECT * FROM sessions 
		#	WHERE sessid = {}""".format(form.session.data)))

		session_id	 = str(uuid.uuid4())  # randomly generated bop session ID
		session_name   = create.session.data  # title given to session
		session_genre  = create.genre.data	# metadata of bop session created

		master_id	  = str(uuid.uuid4()) # ID of master: starts as creator
		participant_id = master_id	# ID of anyone joining: creator automatically in

		c.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", 
			[session_id, session_name, session_genre, master_id, participant_id])
		cur.commit()
		return redirect("/bop/{}/".format(session_id))

	# case of hitting the page after logging in (did not click create)
	else: 
		joinable = c.execute("""SELECT * FROM sessions""").fetchall()
		sessions = c.execute("""SELECT * FROM sessions""").fetchall()
		return render_template("session.html", 
							   joinable=joinable,
							   sessions=sessions,
							   create=create, join=join)

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)