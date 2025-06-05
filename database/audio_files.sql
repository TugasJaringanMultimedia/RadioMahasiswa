-- Buat database
CREATE DATABASE IF NOT EXISTS audio_streaming;
USE audio_streaming;

-- Buat tabel audio_files
CREATE TABLE audio_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_file VARCHAR(255) NOT NULL,
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 10),
    file_path VARCHAR(500),
    file_size BIGINT,
    duration_seconds INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_nama_file (nama_file),
    INDEX idx_rating (rating)
);

-- Insert sample data
INSERT INTO audio_files (nama_file, rating, file_path, file_size, duration_seconds) VALUES
('meeting_recording_001.wav', 8.5, './audio_files/meeting_recording_001.wav', 1024000, 120),
('interview_session.wav', 9.2, './audio_files/interview_session.wav', 2048000, 180),
('conference_call.wav', 7.8, './audio_files/conference_call.wav', 1536000, 150),
('presentation_audio.wav', 8.9, './audio_files/presentation_audio.wav', 1792000, 200),
('discussion_group.wav', 6.5, './audio_files/discussion_group.wav', 1280000, 90);

-- Buat view untuk filter
CREATE VIEW high_rated_files AS
SELECT * FROM audio_files WHERE rating >= 8.0;

CREATE VIEW recent_files AS
SELECT * FROM audio_files ORDER BY created_at DESC LIMIT 10;