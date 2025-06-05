from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import threading
import subprocess
import signal

# Import configuration and models
from config import Config
from database.models import db, Song, Playlist, StreamingSession, ListenerLog
from audio_streaming.server import AudioServer

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, async_mode=Config.SOCKETIO_ASYNC_MODE, cors_allowed_origins="*")

# Global variables
audio_server = None
current_session = None
connected_listeners = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_file_size(file_path):
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def format_duration(seconds):
    """Format duration from seconds to MM:SS"""
    if not seconds:
        return "00:00"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

# Routes
@app.route('/')
def index():
    """Homepage with dashboard"""
    # Get recent songs
    recent_songs = Song.query.filter_by(is_active=True).order_by(Song.upload_date.desc()).limit(10).all()
    
    # Get active streaming session
    active_session = StreamingSession.query.filter_by(status='active').first()
    
    # Get popular songs
    popular_songs = Song.query.filter_by(is_active=True).order_by(Song.play_count.desc()).limit(5).all()
    
    return render_template('index.html', 
                          recent_songs=recent_songs,
                          active_session=active_session,
                          popular_songs=popular_songs,
                          format_duration=format_duration)

@app.route('/live_stream')
def live_stream():
    """Live streaming page"""
    active_session = StreamingSession.query.filter_by(status='active').first()
    return render_template('live_stream.html', active_session=active_session)

@app.route('/recordings')
def recordings():
    """Recordings management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    genre = request.args.get('genre', '', type=str)
    
    query = Song.query.filter_by(is_active=True)
    
    # Apply search filter
    if search:
        query = query.filter(
            (Song.title.contains(search)) |
            (Song.artist.contains(search)) |
            (Song.album.contains(search))
        )
    
    # Apply genre filter
    if genre:
        query = query.filter(Song.genre == genre)
    
    # Get songs with pagination
    songs = query.order_by(Song.upload_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get available genres for filter
    genres = db.session.query(Song.genre).filter(Song.genre.isnot(None)).distinct().all()
    genres = [g[0] for g in genres if g[0]]
    
    return render_template('recordings.html', 
                          songs=songs, 
                          search=search, 
                          genre=genre,
                          genres=genres,
                          format_duration=format_duration)

@app.route('/search')
def search():
    """Search page"""
    query = request.args.get('q', '', type=str)
    results = []
    
    if query:
        results = Song.query.filter(
            (Song.title.contains(query)) |
            (Song.artist.contains(query)) |
            (Song.album.contains(query)) |
            (Song.genre.contains(query))
        ).filter_by(is_active=True).limit(50).all()
    
    return render_template('search.html', query=query, results=results, format_duration=format_duration)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Upload audio file"""
    if request.method == 'POST':
        # Check if file is present
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Secure filename
            filename = secure_filename(file.filename)
            
            # Create upload directory if not exists
            upload_dir = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Get file info
            file_size = get_file_size(file_path)
            
            # Create database entry
            song = Song(
                title=request.form.get('title', filename.rsplit('.', 1)[0]),
                artist=request.form.get('artist', 'Unknown'),
                album=request.form.get('album', ''),
                genre=request.form.get('genre', ''),
                file_path=f'/static/uploads/{filename}',
                file_size=file_size,
                created_by=request.form.get('created_by', 'admin')
            )
            
            db.session.add(song)
            db.session.commit()
            
            flash(f'File {filename} uploaded successfully!')
            return redirect(url_for('recordings'))
        else:
            flash('Invalid file type. Please upload MP3, WAV, OGG, or M4A files.')
    
    return render_template('upload.html')

# API Routes
@app.route('/api/songs')
def api_songs():
    """API endpoint to get songs"""
    songs = Song.query.filter_by(is_active=True).all()
    return jsonify([song.to_dict() for song in songs])

@app.route('/api/songs/<int:song_id>/play', methods=['POST'])
def api_play_song(song_id):
    """API endpoint to increment play count"""
    song = Song.query.get_or_404(song_id)
    song.play_count += 1
    db.session.commit()
    return jsonify({'status': 'success', 'play_count': song.play_count})

@app.route('/api/search')
def api_search():
    """API endpoint for search"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    results = Song.query.filter(
        (Song.title.contains(query)) |
        (Song.artist.contains(query)) |
        (Song.album.contains(query))
    ).filter_by(is_active=True).limit(20).all()
    
    return jsonify([song.to_dict() for song in results])

@app.route('/api/streaming/start', methods=['POST'])
def api_start_streaming():
    """API endpoint to start streaming session"""
    global audio_server, current_session
    
    data = request.get_json()
    session_name = data.get('session_name', 'Live Stream')
    dj_name = data.get('dj_name', 'DJ')
    description = data.get('description', '')
    
    # End any existing session
    if current_session:
        current_session.status = 'ended'
        current_session.end_time = datetime.utcnow()
        db.session.commit()
    
    # Create new session
    current_session = StreamingSession(
        session_name=session_name,
        dj_name=dj_name,
        description=description
    )
    db.session.add(current_session)
    db.session.commit()
    
    # Start audio server if not running
    if not audio_server:
        try:
            audio_server = AudioServer(
                protocol=Config.AUDIO_PROTOCOL,
                port=Config.AUDIO_PORT,
                chunk_size=Config.AUDIO_CHUNK_SIZE
            )
            audio_server.start()
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({
        'status': 'success', 
        'session_id': current_session.id,
        'message': 'Streaming session started'
    })

@app.route('/api/streaming/stop', methods=['POST'])
def api_stop_streaming():
    """API endpoint to stop streaming session"""
    global audio_server, current_session
    
    if current_session:
        current_session.status = 'ended'
        current_session.end_time = datetime.utcnow()
        db.session.commit()
        current_session = None
    
    if audio_server:
        audio_server.stop()
        audio_server = None
    
    return jsonify({'status': 'success', 'message': 'Streaming session stopped'})

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    print(f'Client connected: {client_ip}')
    
    # Add to connected listeners
    connected_listeners[request.sid] = {
        'ip': client_ip,
        'connect_time': datetime.utcnow()
    }
    
    # Update listener count for active session
    if current_session:
        current_session.listener_count = len(connected_listeners)
        db.session.commit()
        
        # Log listener connection
        listener_log = ListenerLog(
            session_id=current_session.id,
            listener_ip=client_ip
        )
        db.session.add(listener_log)
        db.session.commit()
    
    # Send current session info
    emit('session_info', {
        'active_session': current_session.session_name if current_session else None,
        'dj_name': current_session.dj_name if current_session else None,
        'listener_count': len(connected_listeners)
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_info = connected_listeners.pop(request.sid, None)
    if client_info:
        print(f'Client disconnected: {client_info["ip"]}')
        
        # Update listener count
        if current_session:
            current_session.listener_count = len(connected_listeners)
            db.session.commit()

@socketio.on('join_stream')
def handle_join_stream():
    """Handle client joining stream"""
    join_room('live_stream')
    emit('joined_stream', {'status': 'success'})

@socketio.on('leave_stream')
def handle_leave_stream():
    """Handle client leaving stream"""
    leave_room('live_stream')
    emit('left_stream', {'status': 'success'})

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize database
@app.before_first_request
def create_tables():
    """Create database tables"""
    db.create_all()
    
    # Create upload directory
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

def cleanup_on_exit():
    """Cleanup resources on exit"""
    global audio_server, current_session
    
    if current_session:
        current_session.status = 'ended'
        current_session.end_time = datetime.utcnow()
        db.session.commit()
    
    if audio_server:
        audio_server.stop()

# Register cleanup function
import atexit
atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("Starting Radio Mahasiswa Server...")
    print(f"Database: {Config.SQLALCHEMY_DATABASE_URI}")
    print(f"Audio Server: {Config.AUDIO_PROTOCOL.upper()}:{Config.AUDIO_PORT}")
    
    # Run the application
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0', 
                port=5000,
                allow_unsafe_werkzeug=True)