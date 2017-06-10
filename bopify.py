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

# ========================== Helper Functions =============================== #

def join_session(cur, session_id, session_name, session_genre, 
	master_id, participant_id):
	"""Helper function used for joining a room. Automatically redirects to the
	page where all joined rooms are listed

	Args:
	cur           (SQLite cursor): pointer into sessions DB
	session_id    (str): randomly generated bop session ID
	session_name  (str): title given to session
	session_genre (str): metadata of bop session created

	master_id     (str): ID of master of the session
	participant_id(str): ID of the joining member

	Returns:
	bool: Redirection to bop page (listing joined sessions)
	"""

	cur.cursor().execute("INSERT INTO sessions VALUES (?,?,?,?,?)", 
		[session_id, session_name, session_genre, master_id, participant_id])
	cur.commit()
	return redirect("/bop/")

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

@app.route("/bop/", methods=["GET", "POST"])
def bop():
	# DB Columns: sessid | sessname | sessgenre | masterid | partid |
	cur = get_db()
	c   = cur.cursor()
	
	# sessions the user is already a part of: do NOT display on "join" list
	sessions = c.execute("""SELECT * FROM sessions WHERE partid=?""",
		(session['user_id'],)).fetchall()
	session_ids = [session[0] for session in sessions]

	full = c.execute("""SELECT * FROM sessions""").fetchall()
	joinable = [session for session in full if session[0] not in session_ids]

	create = CreateForm()
	join   = JoinForm()
	join.session.choices = [(session[0], session[1]) for session in joinable]
	
	# case where the person just created a new session: creates a 
	# new entry in DB and redirects them to the session page
	if create.validate_on_submit() and create.create.data:
		return join_session(cur=cur, 
					session_id=str(uuid.uuid4()), 
					session_name=create.session.data, 
					session_genre=create.genre.data, 
					master_id=session['user_id'], 
					participant_id=session['user_id'])

	elif join.validate_on_submit():
		reference = c.execute("""SELECT * FROM sessions WHERE sessid=?""",
			(join.session.data,)).fetchone()
		return join_session(cur=cur, 
					session_id=reference[0], 
					session_name=reference[1], 
					session_genre=reference[2], 
					master_id=reference[3], 
					participant_id=session['user_id'])

	# case of hitting the page after logging in (did not click create)
	return render_template("session.html", 
							joinable=joinable,
							sessions=sessions,
							create=create, join=join)

@app.route("/room/")
def room():
	return render_template("bop.html")

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)