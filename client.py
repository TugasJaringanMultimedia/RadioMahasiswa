# client.py - Updated with database integration
import socket
import argparse
import signal
import pyaudio
import sys
import queue
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
    global recordStream, client_socket, pyaudioObj
    print("\nExiting the program")
    if 'recordStream' in globals():
        recordStream.stop_stream()
        recordStream.close()
    if 'pyaudioObj' in globals():
        pyaudioObj.terminate()
    if 'client_socket' in globals():
        client_socket.close()
    sys.exit(0)

signal.signal(signal.SIGINT, handler)

parser = argparse.ArgumentParser(description="AudioStream client with database integration")
parser.add_argument("--protocol", required=False, default='tcp', choices=['udp', 'tcp'])
parser.add_argument("--host", required=True, help="Server IP address")
parser.add_argument("--port", required=False, default=12345, type=int)
parser.add_argument("--size", required=False, default=10, type=int, choices=range(10, 151, 10))
parser.add_argument("--session-name", required=False, help="Name for this audio session")
parser.add_argument("--expected-rating", required=False, type=float, default=7.0, 
                    help="Expected quality rating for this session (0-10)")
args = parser.parse_args()

print(f"Connecting to {args.host}:{args.port} using {args.protocol.upper()}")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 441
NUMCHUNKS = int(args.size / 10)

sendQueue = queue.Queue()
silence = 0
silenceData = silence.to_bytes(2) * CHUNK * NUMCHUNKS
sequenceNumber = 0
session_start_time = datetime.now()

# Session tracking
bytes_sent = 0
packets_sent = 0

def record(data, frame_count, time_info, status):
    global sendQueue
    sendQueue.put(data)
    return (silenceData, pyaudio.paContinue)

pyaudioObj = pyaudio.PyAudio()

try:
    recordStream = pyaudioObj.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=NUMCHUNKS * CHUNK,
                                  stream_callback=record)
except Exception as e:
    print(f"Error opening audio stream: {e}")
    sys.exit(1)

print("PyAudio Device Initialized")

try:
    if args.protocol == 'udp':
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    else:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((args.host, args.port))
    
    # Send session metadata to server
    if args.session_name and args.protocol == 'tcp':
        metadata = f"SESSION_NAME:{args.session_name}|RATING:{args.expected_rating}".encode()
        client_socket.sendall(len(metadata).to_bytes(4, 'little') + metadata)
        
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)

def sendAudio():
    global client_socket, sequenceNumber, sendQueue, bytes_sent, packets_sent
    
    try:
        audioData = sendQueue.get()
        seqBytes = sequenceNumber.to_bytes(2, byteorder="little", signed=False)
        sendData = seqBytes + audioData

        print(f"Sending Sequence #{sequenceNumber} ({len(sendData)} bytes)")

        if args.protocol == 'udp':
            client_socket.sendto(sendData, (args.host, args.port))
        else:
            client_socket.sendall(sendData)

        bytes_sent += len(sendData)
        packets_sent += 1
        sequenceNumber = (sequenceNumber + 1) % 65536
        
    except Exception as e:
        print(f"Error sending audio: {e}")
        handler(signal.SIGINT, None)

def log_session_end():
    """Log session statistics"""
    session_duration = (datetime.now() - session_start_time).total_seconds()
    print(f"\nSession Statistics:")
    print(f"Duration: {session_duration:.1f} seconds")
    print(f"Packets sent: {packets_sent}")
    print(f"Bytes sent: {bytes_sent}")
    print(f"Average bitrate: {(bytes_sent * 8) / session_duration / 1000:.1f} kbps")

# Register cleanup function
import atexit
atexit.register(log_session_end)

print("Starting audio transmission... Press Ctrl+C to stop")
recordStream.start_stream()

try:
    while True:
        sendAudio()
except KeyboardInterrupt:
    handler(signal.SIGINT, None)