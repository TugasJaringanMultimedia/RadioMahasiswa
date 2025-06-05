# server.py - Updated with database integration

import socket
import argparse
import signal
import pyaudio
import sys
import wave
import os
from datetime import datetime

# Import database functionality
try:
    from database.database import AudioFileDatabase
    DATABASE_AVAILABLE = True
except ImportError:
    print("Warning: Database module not available. Running without database integration.")
    DATABASE_AVAILABLE = False

def handler(signum, frame):
    global playStream, server_socket, connection, output_file, pyaudioObj
    print("\nExiting the program")
    
    # Save to database before closing
    if args.save and DATABASE_AVAILABLE and session_info['file_saved']:
        save_to_database()
    
    if 'playStream' in globals():
        playStream.stop_stream()
        playStream.close()
    if 'pyaudioObj' in globals():
        pyaudioObj.terminate()
    if 'connection' in globals() and connection:
        connection.close()
    if 'server_socket' in globals():
        server_socket.close()
    if 'output_file' in globals() and output_file:
        output_file.close()
    
    print_session_stats()
    sys.exit(0)

signal.signal(signal.SIGINT, handler)

parser = argparse.ArgumentParser(description="AudioStream server with database integration")
parser.add_argument("--protocol", required=False, default='tcp', choices=['udp', 'tcp'])
parser.add_argument("--port", required=False, default=12345, type=int)
parser.add_argument("--size", required=False, default=10, type=int, choices=range(10, 151, 10))
parser.add_argument("--save", required=False, help="Save audio to file (WAV format)")
parser.add_argument("--auto-rate", action='store_true', 
                    help="Automatically rate audio quality based on packet loss")
parser.add_argument("--save-dir", required=False, default="./audio_files", 
                    help="Directory to save audio files")
args = parser.parse_args()

# Create save directory if it doesn't exist
if args.save and not os.path.exists(args.save_dir):
    os.makedirs(args.save_dir)

print(f"Starting server on port {args.port} using {args.protocol.upper()}")
if args.save:
    print(f"Audio will be saved to {args.save}")
if DATABASE_AVAILABLE:
    print("Database integration enabled")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 441
NUMCHUNKS = int(args.size / 10)

# Session tracking
session_info = {
    'start_time': datetime.now(),
    'packets_received': 0,
    'packets_lost': 0,
    'bytes_received': 0,
    'session_name': None,
    'expected_rating': 7.0,
    'calculated_rating': 0.0,
    'file_saved': False
}

pyaudioObj = pyaudio.PyAudio()

try:
    playStream = pyaudioObj.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=RATE,
                               output=True,
                               frames_per_buffer=CHUNK * NUMCHUNKS)
except Exception as e:
    print(f"Error opening audio stream: {e}")
    sys.exit(1)

silence = 0
silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS
output_file = None

# Setup audio file saving
if args.save:
    try:
        # Generate filename if not specified
        if not args.save.endswith('.wav'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.save = os.path.join(args.save_dir, f"audio_session_{timestamp}.wav")
        
        output_file = wave.open(args.save, 'wb')
        output_file.setnchannels(CHANNELS)
        output_file.setsampwidth(pyaudio.get_sample_size(FORMAT))
        output_file.setframerate(RATE)
        print(f"Recording to: {args.save}")
    except Exception as e:
        print(f"Error opening output file: {e}")
        output_file = None

# Socket setup
if args.protocol == 'udp':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('0.0.0.0', args.port))
    connection = None
else:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', args.port))
    server_socket.listen(1)
    print("Waiting for connection...")
    connection, source = server_socket.accept()
    print(f"Connected to {source[0]}:{source[1]}")
    
    # Receive session metadata
    try:
        metadata_length = int.from_bytes(connection.recv(4), 'little')
        if metadata_length > 0:
            metadata = connection.recv(metadata_length).decode()
            for item in metadata.split('|'):
                if ':' in item:
                    key, value = item.split(':', 1)
                    if key == 'SESSION_NAME':
                        session_info['session_name'] = value
                    elif key == 'RATING':
                        session_info['expected_rating'] = float(value)
            print(f"Session: {session_info['session_name']}, Expected Rating: {session_info['expected_rating']}")
    except:
        pass  # Continue without metadata

expectedSeqNum = 0

def calculate_quality_rating():
    """Calculate audio quality rating based on packet loss and other factors"""
    if session_info['packets_received'] == 0:
        return 0.0
    
    packet_loss_rate = session_info['packets_lost'] / (session_info['packets_received'] + session_info['packets_lost'])
    
    # Base rating starts at 10
    rating = 10.0
    
    # Reduce rating based on packet loss
    rating -= packet_loss_rate * 5.0  # Max 5 points deduction for packet loss
    
    # Ensure rating is between 0 and 10
    rating = max(0.0, min(10.0, rating))
    
    return round(rating, 1)

def save_to_database():
    """Save session information to database"""
    if not DATABASE_AVAILABLE or not args.save:
        return
    
    try:
        db = AudioFileDatabase()
        
        # Calculate final metrics
        session_duration = (datetime.now() - session_info['start_time']).total_seconds()
        file_size = os.path.getsize(args.save) if os.path.exists(args.save) else 0
        
        # Use calculated rating if auto-rate is enabled, otherwise use expected rating
        final_rating = session_info['calculated_rating'] if args.auto_rate else session_info['expected_rating']
        
        # Generate session name if not provided
        if not session_info['session_name']:
            session_info['session_name'] = os.path.basename(args.save)
        
        # Add to database
        file_id = db.add_audio_file(
            nama_file=session_info['session_name'],
            rating=final_rating,
            file_path=args.save,
            file_size=file_size,
            duration_seconds=int(session_duration)
        )
        
        if file_id:
            print(f"Session saved to database with ID: {file_id}")
        else:
            print("Failed to save session to database")
            
    except Exception as e:
        print(f"Error saving to database: {e}")

def print_session_stats():
    """Print session statistics"""
    session_duration = (datetime.now() - session_info['start_time']).total_seconds()
    print(f"\nSession Statistics:")
    print(f"Duration: {session_duration:.1f} seconds")
    print(f"Packets received: {session_info['packets_received']}")
    print(f"Packets lost: {session_info['packets_lost']}")
    print(f"Bytes received: {session_info['bytes_received']}")
    if session_info['packets_received'] > 0:
        loss_rate = session_info['packets_lost'] / (session_info['packets_received'] + session_info['packets_lost']) * 100
        print(f"Packet loss rate: {loss_rate:.2f}%")
    print(f"Calculated quality rating: {session_info['calculated_rating']}")

def recvData():
    global expectedSeqNum, connection, output_file, session_info
    
    print(f"Expecting Sequence #{expectedSeqNum}")

    try:
        if args.protocol == 'udp':
            data, address = server_socket.recvfrom(CHUNK * NUMCHUNKS * 2 + 2)
        else:
            data = connection.recv(CHUNK * NUMCHUNKS * 2 + 2)
            while len(data) < CHUNK * NUMCHUNKS * 2 + 2:
                more_data = connection.recv(CHUNK * NUMCHUNKS * 2 + 2 - len(data))
                if not more_data:
                    break
                data += more_data
    except Exception as e:
        print(f"Error receiving data: {e}")
        handler(signal.SIGINT, None)
        return

    if len(data) < 2:
        return

    sequenceNumber = int.from_bytes(data[:2], byteorder="little", signed=False)
    audioData = data[2:]
    
    session_info['bytes_received'] += len(data)

    if expectedSeqNum == sequenceNumber:
        print(f"Received Sequence #{sequenceNumber} ({len(data)} bytes)")
        playStream.write(audioData)
        if output_file:
            output_file.writeframes(audioData)
            session_info['file_saved'] = True
        session_info['packets_received'] += 1
        expectedSeqNum = (expectedSeqNum + 1) % 65536
    else:
        print(f"Received Out of Sequence #{sequenceNumber} ({len(data)} bytes) - Expected {expectedSeqNum}")
        playStream.write(silenceData)
        
        # Count missed packets
        if sequenceNumber > expectedSeqNum:
            missed_packets = sequenceNumber - expectedSeqNum
            session_info['packets_lost'] += missed_packets
            expectedSeqNum = (sequenceNumber + 1) % 65536
        else:
            session_info['packets_lost'] += 1
    
    # Update calculated rating periodically
    if session_info['packets_received'] % 100 == 0:  # Every 100 packets
        session_info['calculated_rating'] = calculate_quality_rating()

# Register cleanup function
import atexit
atexit.register(lambda: save_to_database() if args.save and DATABASE_AVAILABLE and session_info['file_saved'] else None)

print("Server ready. Waiting for audio data... Press Ctrl+C to stop")

try:
    while True:
        recvData()
except KeyboardInterrupt:
    handler(signal.SIGINT, None)
