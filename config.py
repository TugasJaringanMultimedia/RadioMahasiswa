import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-radio-mahasiswa'
    
    # Database Configuration (XAMPP MySQL)
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''  # Default XAMPP password is empty
    MYSQL_DB = 'radio_mahasiswa'
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    
    # Audio Streaming Configuration
    AUDIO_HOST = 'localhost'
    AUDIO_PORT = 12345
    AUDIO_PROTOCOL = 'udp'  # or 'tcp'
    AUDIO_CHUNK_SIZE = 10  # milliseconds
    
    # SocketIO Configuration
    SOCKETIO_ASYNC_MODE = 'eventlet'