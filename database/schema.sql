-- Database schema for Radio Mahasiswa
CREATE DATABASE IF NOT EXISTS radio_mahasiswa;
USE radio_mahasiswa;

-- Songs table for storing audio metadata
CREATE TABLE songs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255),
    album VARCHAR(255),
    genre VARCHAR(100),
    duration INT, -- in seconds
    file_path VARCHAR(500),
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    play_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    INDEX idx_title (title),
    INDEX idx_artist (artist),
    INDEX idx_genre (genre),
    INDEX idx_upload_date (upload_date)
);

-- Playlists table
CREATE TABLE playlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100)
);

-- Playlist songs relation
CREATE TABLE playlist_songs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id INT,
    song_id INT,
    position INT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Live streaming sessions
CREATE TABLE streaming_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_name VARCHAR(255),
    dj_name VARCHAR(100),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    status ENUM('active', 'ended') DEFAULT 'active',
    listener_count INT DEFAULT 0,
    description TEXT
);

-- Listener logs
CREATE TABLE listener_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT,
    listener_ip VARCHAR(45),
    connect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnect_time TIMESTAMP NULL,
    FOREIGN KEY (session_id) REFERENCES streaming_sessions(id) ON DELETE CASCADE
);

-- Insert sample data
INSERT INTO songs (title, artist, album, genre, duration, file_path, created_by) VALUES
('Sample Song 1', 'Local Artist', 'Demo Album', 'Rock', 180, '/uploads/sample1.mp3', 'admin'),
('Campus Radio Intro', 'Radio Team', 'Station ID', 'Jingle', 30, '/uploads/intro.mp3', 'admin'),
('Study Music', 'Instrumental', 'Focus', 'Ambient', 240, '/uploads/study.mp3', 'admin');

INSERT INTO playlists (name, description, created_by) VALUES
('Morning Show', 'Lagu-lagu untuk program pagi', 'admin'),
('Study Time', 'Musik untuk belajar', 'admin'),
('Rock Hits', 'Lagu rock terpopuler', 'admin');