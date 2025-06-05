from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Song(db.Model):
    __tablename__ = 'songs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255))
    album = db.Column(db.String(255))
    genre = db.Column(db.String(100))
    duration = db.Column(db.Integer)  # in seconds
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)
    upload_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    play_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Song {self.title} by {self.artist}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'duration': self.duration,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'play_count': self.play_count,
            'is_active': self.is_active,
            'created_by': self.created_by
        }

class Playlist(db.Model):
    __tablename__ = 'playlists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Playlist {self.name}>'

class PlaylistSong(db.Model):
    __tablename__ = 'playlist_songs'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    position = db.Column(db.Integer)
    added_date = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    playlist = db.relationship('Playlist', backref=db.backref('playlist_songs', lazy=True))
    song = db.relationship('Song', backref=db.backref('playlist_songs', lazy=True))

class StreamingSession(db.Model):
    __tablename__ = 'streaming_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(255))
    dj_name = db.Column(db.String(100))
    start_time = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    end_time = db.Column(db.TIMESTAMP)
    status = db.Column(db.Enum('active', 'ended'), default='active')
    listener_count = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<StreamingSession {self.session_name} by {self.dj_name}>'

class ListenerLog(db.Model):
    __tablename__ = 'listener_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('streaming_sessions.id'))
    listener_ip = db.Column(db.String(45))
    connect_time = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    disconnect_time = db.Column(db.TIMESTAMP)
    
    session = db.relationship('StreamingSession', backref=db.backref('listener_logs', lazy=True))