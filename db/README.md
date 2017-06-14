Database(s) are maintained as SQLite for clean implementation. The main
ones are organized as follows:

- Sessions (sessions.db)
- Users    (users.db)

# Sessions
The sessions DB contains all the sessions that have been created along with
all the associated users that have listened to that session. It also tracks
the associated master node user and meta data regarding the session, i.e.
type of music typically played and session title

Organized as:

| Session ID | Session Name | Master | Participants ID | 

- Session ID: ID associated with the session in the DB
- Session Name: Name given to the session (plaintext)
- Master: ID associated with the user who's the master of the session
- Participant ID: ID of the user joining

# Songs
The song DB contains each of the session, simply being the list of songs
associated with a given room and ordering metadata.

| Session ID | Song ID (Spotify) | Song Name | Order | Is_master |

- Session ID: ID associated with the session in the DB
- Song ID (Spotify): Song ID given by Spotify
- Song Name: Song name (plaintext)
- Order: Order in the queue of the song
- Is_master: Whether or not the song was added to the queue by session master