"""
__name__		= bopify.py
__author__		= Cheetrios
__description__ = Main application file for deployment
"""

import uuid
import sqlite3

import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

from flask import Flask, render_template, request, redirect, url_for, session
from flask_oauthlib.client import OAuth, OAuthException
from flask import g

from forms import CreateForm, JoinForm, SearchForm

SESS_DB = "db/sessions.db"
SONG_DB = "db/song.db"

SPOTIFY_APP_ID	   = "d251ae2dd5824052874019013ee73eb0"
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

def get_db(db_fname):
	"""Helper function used for getting DB cursor object given the filename
	of where the SQLite file is saved

	Args:
	db_fname (str): filename of which DB the target cursor will point into

	Returns: SQLite cursor object to DB specified
	"""
	db = getattr(g, "_database", None)
	if db is None:
		g._database = sqlite3.connect(db_fname)
		db = g._database
	return db

def create_sess_db(cur):
	"""Helper function used for setting up the sessions DB 
	given a cursor into the DB. DB is setup per:

	| Session ID | Session Name | Master | Participants ID | 

	Args:
	cur		   (SQLite cursor): pointer into sessions DB

	Returns: Void
	"""
	cur.execute("""CREATE TABLE sessions
	   (sessid  text, sessname text, sessgenre text, 
		masterid text, partid text)""")
	cur.commit()

def delete_sess_db(cur):
	"""Drops the sessions table. Do NOT call unless cleaning up testing

	Args:
	cur		   (SQLite cursor): pointer into sessions DB

	Returns: Void
	"""
	cur.execute("DROP TABLE sessions")
	cur.commit()

def create_song_db(cur):
	"""Helper function used for setting up the songs DB (for sessions->song
	mapping lookups) given a cursor into the DB. DB is setup per:

	| Session ID | Song ID (Spotify) | Position |

	Args:
	cur		   (SQLite cursor): pointer into songs DB

	Returns: Void
	"""
	cur.execute("""CREATE TABLE songs
	   (sessid text, songid text, position real)""")
	cur.commit()

def delete_song_db(cur):
	"""Drops the songs table. Do NOT call unless cleaning up testing

	Args:
	cur		   (SQLite cursor): pointer into songs DB

	Returns: Void
	"""
	cur.execute("DROP TABLE songs")
	cur.commit()

# ========================== Helper Functions =============================== #

def join_session(cur, session_id, session_name, session_genre, 
	master_id, participant_id):
	"""Helper function used for joining a room. Automatically redirects to the
	page where all joined rooms are listed

	Args:
	cur		   (SQLite cursor): pointer into sessions DB
	session_id	(str): randomly generated bop session ID
	session_name  (str): title given to session
	session_genre (str): metadata of bop session created

	master_id	 (str): ID of master of the session
	participant_id(str): ID of the joining member

	Returns: Void
	"""

	cur.cursor().execute("INSERT INTO sessions VALUES (?,?,?,?,?)", 
		[session_id, session_name, session_genre, master_id, participant_id])
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

@app.route("/bop/", methods=["GET", "POST"])
def bop():
	# DB Columns: sessid | sessname | sessgenre | masterid | partid |
	cur = get_db(SESS_DB)
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
		session_id = str(uuid.uuid4())
		join_session(cur=cur, 
					session_id=session_id, 
					session_name=create.session.data, 
					session_genre=create.genre.data, 
					master_id=session['user_id'], 
					participant_id=session['user_id'])
		return redirect(url_for("room", sessid=session_id))

	elif join.validate_on_submit():
		reference = c.execute("""SELECT * FROM sessions WHERE sessid=?""",
			(join.session.data,)).fetchone()
		join_session(cur=cur, 
					session_id=reference[0], 
					session_name=reference[1], 
					session_genre=reference[2], 
					master_id=reference[3], 
					participant_id=session['user_id'])
		return redirect("/bop/")

	# case of hitting the page after logging in (did not click create)
	return render_template("session.html", 
							joinable=joinable,
							sessions=sessions,
							create=create, join=join)

@app.route("/room/<sessid>/", methods=["GET", "POST"])
def room(sessid):
	# | sessid | songid | position
	cur = get_db(SONG_DB)
	
	search = SearchForm()
	client_credentials_manager = SpotifyClientCredentials()
	sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

	songs = []
	if search.validate_on_submit():
		query = search.query.data
		songs = sp.search(q=query)["tracks"]["items"]
	
	return render_template("room.html",
							search=search,
							songs=songs)

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)