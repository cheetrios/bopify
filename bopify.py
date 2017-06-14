"""
__name__		= bopify.py
__author__		= Cheetrios
__description__ = Main application file for deployment
"""

import uuid
import sqlite3
import requests
import base64
import urllib
import json

import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

from flask import Flask, render_template, request, redirect, url_for
from flask import session as flask_session
from flask_oauthlib.client import OAuth, OAuthException
from flask import g

from forms import CreateForm, JoinForm, SearchForm

SESS_DB = "db/sessions.db"
SONG_DB = "db/song.db"

#  Client Keys
CLIENT_ID     = "d251ae2dd5824052874019013ee73eb0"
CLIENT_SECRET = "ee5c56305aea428b986c4a0964361cb2"

# Spotify URLS
SPOTIFY_AUTH_URL     = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL    = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"

API_VERSION     = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)
REDIRECT_URI    = "http://localhost:5000/login/authorized/"
SCOPE           = "playlist-modify-public playlist-modify-private"

app = Flask(__name__)
app.config.from_object("config")

oauth = OAuth(app)

# ========================== DB Setup Functions ============================= #
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

	| Session ID | Song ID (Spotify) | Song Name | Order | Is_master

	Args:
	cur		   (SQLite cursor): pointer into songs DB

	Returns: Void
	"""
	cur.execute("""CREATE TABLE songs
		(sessid text, songid text, songname text, 
		position integer, ismaster integer)""")
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

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)

@app.route("/login/authorized/")
def spotify_authorized():
	"""Logs user in and saves information (ID) into session for DB access

	Args:
	Returns: Redirection to bop sessions listing page
	"""
	# Requests refresh and access tokens
	auth_token = request.args['code']
	code_payload = {
		"grant_type": "authorization_code",
		"code": str(auth_token),
		"redirect_uri": REDIRECT_URI
	}

	base64encoded = base64.b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET))
	headers       = {"Authorization": "Basic {}".format(base64encoded)}
	post_request  = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

	# Tokens are Returned to Application
	response_data = json.loads(post_request.text)
	access_token  = response_data["access_token"]
	refresh_token = response_data["refresh_token"]
	token_type    = response_data["token_type"]
	expires_in    = response_data["expires_in"]

	# Use the access token to access Spotify API
	authorization_header = {"Authorization":"Bearer {}".format(access_token)}

	# Get profile data
	user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
	profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
	profile_data = json.loads(profile_response.text)

	# used to confirm that a user has logged in (for finding sessions)
	flask_session["user_id"] = profile_data["id"]
	return redirect(url_for("bop"))

@app.route("/bop/", methods=["GET", "POST"])
def bop():
	"""Main sessions page where session can be created or joined. Post requests
	can be one of two: create or join, where the first makes new session and
	makes current user the master and the second adding the user as a member.

	Args:
	Returns: Redirection to the particular room page if a new room was created or
	a repopulated version of the sessions landing page
	"""
	# DB Columns: sessid | sessname | sessgenre | masterid | partid |
	cur = sqlite3.connect(SESS_DB)
	c   = cur.cursor()
	
	# sessions the user is already a part of: do NOT display on "join" list
	sessions = c.execute("""SELECT * FROM sessions WHERE partid=?""",
		(flask_session["user_id"],)).fetchall()
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
					master_id=flask_session["user_id"], 
					participant_id=flask_session["user_id"])
		return redirect(url_for("room", sessid=session_id))

	elif join.validate_on_submit():
		reference = c.execute("""SELECT * FROM sessions WHERE sessid=?""",
			(join.session.data,)).fetchone()
		join_session(cur=cur, 
					session_id=reference[0], 
					session_name=reference[1], 
					session_genre=reference[2], 
					master_id=reference[3], 
					participant_id=flask_session["user_id"])
		return redirect("/bop/")

	# case of hitting the page after logging in (did not click create)
	return render_template("session.html", 
							joinable=joinable,
							sessions=sessions,
							create=create, join=join)

@app.route("/room/<sessid>/", methods=["GET", "POST"])
def room(sessid):
	"""Page associated to a particular bop session, showing songs in the room.
	Post requests correspond to when a request to add a song has been made

	Args:
	sessid (str): bop session ID room corresponds to (from DB)
	
	Returns: Bop session room page
	"""
	# determines whether or not current user is master
	sess_cur = sqlite3.connect(SESS_DB) # | sessid | sessname | sessgenre | masterid | partid |
	reference = sess_cur.cursor().execute(
		"""SELECT * FROM sessions WHERE sessid=?""", (sessid,)).fetchone()
	is_master = (reference is None or reference[3] == flask_session["user_id"]) 
	
	song_cur = sqlite3.connect(SONG_DB) # | sessid | songid | songname | position | ismaster
	songs = song_cur.cursor().execute(
		"""SELECT * FROM songs WHERE sessid=?""", (sessid,)).fetchall()
	
	search = SearchForm()
	client_credentials_manager = SpotifyClientCredentials()
	sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

	queried = []

	# if user is searching for a song
	if search.validate_on_submit():
		query = search.query.data
		queried = sp.search(q=query)["tracks"]["items"]
		
	# when the master presses "play"
	elif request.method == "POST" and "play" in request.form:
		song = song_cur.cursor().execute(
		"""SELECT * FROM songs 
			WHERE sessid=?
			AND ismaster=1
			ORDER BY position ASC""", (sessid,)).fetchone()

	# when the master accepts the proposal and adds the song
	elif request.method == "POST" and "add" in request.form:
		song_id = request.form.split(":")[1] # ID passed in through form name
		song_cur.cursor().execute(
		"""UPDATE songs
			SET ismaster=1,
	        WHERE songid=?""", (song_id,))
		song_cur.commit()

	return render_template("room.html",
							search=search,
							is_master=is_master,
							sessid=sessid,
							songs=songs,
							queried=queried)

@app.route("/room/<sessid>/<songid>/<songname>/<ismaster>/")
def queue(sessid, songid, songname, ismaster):
	"""Reqeusts particular song to be added to the session queue. 
	INSECURE -- should not be able to easily modify URL to make "master request"

	Args:
	sessid (str): bop session ID room corresponds to (from sessions DB)
	songid (str): song ID to be played (from songs DB)
	songname (str): name of song to be played
	ismaster (int): 1/0 int to indicate whether request is coming from
		the session master or other participant respectively

	Returns: Redirection to the bop session page
	"""
	cur = sqlite3.connect(SONG_DB)
	songs = cur.cursor().execute(
		"""SELECT * FROM songs WHERE sessid=?""", (sessid,)).fetchall()
	cur.cursor().execute("INSERT INTO songs VALUES (?,?,?,?,?)", 
		[sessid, songid, songname, len(songs) + 1, ismaster])
	cur.commit()
	return redirect(url_for("room", sessid=sessid))

if __name__ == "__main__":
	app.run(host="0.0.0.0", debug=True)