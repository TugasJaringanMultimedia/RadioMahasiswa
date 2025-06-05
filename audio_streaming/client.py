import socket
import argparse
import signal
import pyaudio
import sys
import queue
import threading
import time
from datetime import datetime

class AudioClient:
    def __init__(self, protocol='udp', host='localhost', port=12345, chunk_size=10):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.chunk_size = chunk_size
        self.is_running = False
        self.is_recording = False
        
        # Audio configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 441  # 10 ms
        self.NUMCHUNKS = int(chunk_size / 10)
        
        # Initialize PyAudio
        self.pyaudio_obj = pyaudio.PyAudio()
        
        # Audio data queue
        self.send_queue = queue.Queue()
        
        # Sequence number
        self.sequence_number = 0
        
        # Setup silence data
        silence = 0
        self.silence_data = silence.to_bytes(2) * self.CHUNK * self.NUMCHUNKS
        
        # Setup socket
        self.setup_socket()
        
        # Setup audio recording
        self.setup_recording()
        
        print(f"Audio Client initialized - Protocol: {protocol.upper()}, Host: {host}, Port: {port}")
    
    def setup_socket(self):
        """Setup socket connection"""
        if self.protocol == 'udp':
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.destination = (self.host, self.port)
        else:  # TCP
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.client_socket.connect((self.host, self.port))
                print(f"Connected to TCP server at {self.host}:{self.port}")
            except Exception as e:
                print(f"Failed to connect to TCP server: {e}")
                raise
        
        print("Socket connection established")
    
    def record_callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio recording"""
        if self.is_recording:
            self.send_queue.put(in_data)
        return (self.silence_data, pyaudio.paContinue)
    
    def setup_recording(self):
        """Setup audio recording stream"""
        try:
            self.record_stream = self.pyaudio_obj.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.NUMCHUNKS * self.CHUNK,
                stream_callback=self.record_callback
            )
            print("Audio recording stream initialized")
        except Exception as e:
            print(f"Failed to initialize recording stream: {e}")
            raise
    
    def send_audio_data(self):
        """Send audio data to server"""
        while self.is_running:
            try:
                # Get audio data from queue (with timeout)
                audio_data = self.send_queue.get(timeout=1.0)
                
                # Create packet with sequence number
                seq_bytes = self.sequence_number.to_bytes(2, byteorder="little", signed=False)
                send_data = seq_bytes + audio_data
                
                # Send data
                try:
                    if self.protocol == 'udp':
                        self.client_socket.sendto(send_data, self.destination)
                    else:  # TCP
                        self.client_socket.sendall(send_data)
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent Sequence #{self.sequence_number} ({len(send_data)} bytes)")
                    
                    # Increment sequence number
                    self.sequence_number = (self.sequence_number + 1) % 65536
                    
                except socket.error as e:
                    print(f"Socket error while sending: {e}")
                    if self.protocol == 'tcp':
                        # Try to reconnect for TCP
                        self.reconnect()
                
            except queue.Empty:
                # Timeout occurred, continue loop
                continue
            except Exception as e:
                print(f"Error in send_audio_data: {e}")
    
    def reconnect(self):
        """Attempt to reconnect TCP connection"""
        if self.protocol == 'tcp':
            print("Attempting to reconnect...")
            try:
                self.client_socket.close()
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                print("Reconnected successfully")
            except Exception as e:
                print(f"Reconnection failed: {e}")
    
    def start_recording(self):
        """Start audio recording"""
        if not self.is_recording:
            self.is_recording = True
            self.record_stream.start_stream()
            print("Audio recording started")
    
    def stop_recording(self):
        """Stop audio recording"""
        if self.is_recording:
            self.is_recording = False
            print("Audio recording stopped")
    
    def start(self):
        """Start the audio client"""
        self.is_running = True
        
        # Start sending thread
        self.send_thread = threading.Thread(target=self.send_audio_data)
        self.send_thread.daemon = True
        self.send_thread.start()
        
        # Start recording
        self.start_recording()
        
        print("Audio client started")
        print("Recording and streaming audio...")
        print("Press Ctrl+C to stop")
    
    def stop(self):
        """Stop the audio client"""
        print("Stopping audio client...")
        self.is_running = False
        self.stop_recording()
        
        # Stop and close recording stream
        if hasattr(self, 'record_stream'):
            self.record_stream.stop_stream()
            self.record_stream.close()
        
        # Close socket
        if hasattr(self, 'client_socket'):
            self.client_socket.close()
        
        # Close PyAudio
        if hasattr(self, 'pyaudio_obj'):
            self.pyaudio_obj.terminate()
        
        print("Audio client stopped")
    
    def list_audio_devices(self):
        """List available audio devices"""
        print("\nAvailable Audio Devices:")
        print("-" * 50)
        for i in range(self.pyaudio_obj.get_device_count()):
            device_info = self.pyaudio_obj.get_device_info_by_index(i)
            print(f"Device {i}: {device_info['name']}")
            print(f"  Max Input Channels: {device_info['maxInputChannels']}")
            print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")
            print()

# Global client instance
audio_client = None

def signal_handler(signum, frame):
    """Handle interrupt signal"""
    global audio_client
    print("\nReceived interrupt signal...")
    if audio_client:
        audio_client.stop()
    sys.exit(0)

def main():
    global audio_client
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Audio Stream Client")
    parser.add_argument("--protocol", required=False, default='udp',
                       choices=['udp', 'tcp'], help="Protocol to use")
    parser.add_argument("--host", required=False, default="localhost",
                       help="Server host address")
    parser.add_argument("--port", required=False, default=12345, type=int,
                       help="Server port")
    parser.add_argument("--size", required=False, default=10, type=int,
                       choices=range(10, 151, 10), help="Chunk size in milliseconds")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices")
    
    args = parser.parse_args()
    
    try:
        # Create client
        audio_client = AudioClient(
            protocol=args.protocol,
            host=args.host,
            port=args.port,
            chunk_size=args.size
        )
        
        # List devices if requested
        if args.list_devices:
            audio_client.list_audio_devices()
            return
        
        # Start client
        audio_client.start()
        
        # Keep client running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        if audio_client:
            audio_client.stop()

if __name__ == "__main__":
    main()