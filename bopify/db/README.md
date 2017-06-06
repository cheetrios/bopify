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

| Session ID | Session Name | Master | Participants IDs | 

# Users
The users DB contains each of the users, their associated metadata, and all
of the sessions they are a part of.

| User ID | Metadata | Session IDs |