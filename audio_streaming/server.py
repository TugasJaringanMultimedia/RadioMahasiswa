import socket
import argparse
import signal
import pyaudio
import sys
import threading
import time
from datetime import datetime

class AudioServer:
    def __init__(self, protocol='udp', port=12345, chunk_size=10):
        self.protocol = protocol
        self.port = port
        self.chunk_size = chunk_size
        self.is_running = False
        self.clients = set()  # For TCP connections
        self.listener_count = 0
        
        # Audio configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 441  # 10 ms
        self.NUMCHUNKS = int(chunk_size / 10)
        
        # Initialize PyAudio
        self.pyaudio_obj = pyaudio.PyAudio()
        
        # Setup silence data
        silence = 0
        self.silence_data = silence.to_bytes(2) * self.CHUNK * self.NUMCHUNKS
        
        # Initialize play stream
        self.play_stream = self.pyaudio_obj.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK * self.NUMCHUNKS
        )
        
        # Socket setup
        self.setup_socket()
        
        # Expected sequence number
        self.expected_seq_num = 0
        
        print(f"Audio Server initialized - Protocol: {protocol.upper()}, Port: {port}")
    
    def setup_socket(self):
        """Setup socket based on protocol"""
        if self.protocol == 'udp':
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.bind(('', self.port))
        else:  # TCP
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
        
        print("Socket initialized successfully")
    
    def handle_tcp_client(self, connection, address):
        """Handle individual TCP client connection"""
        print(f"New TCP client connected: {address}")
        self.clients.add(connection)
        self.listener_count += 1
        
        try:
            while self.is_running:
                try:
                    data = connection.recv(self.CHUNK * self.NUMCHUNKS * 2 + 2)
                    if not data:
                        break
                    
                    # Ensure we receive complete packet
                    while len(data) < self.CHUNK * self.NUMCHUNKS * 2 + 2:
                        more_data = connection.recv(self.CHUNK * self.NUMCHUNKS * 2 + 2 - len(data))
                        if not more_data:
                            break
                        data += more_data
                    
                    self.process_audio_data(data, address)
                    
                except socket.error:
                    break
        except Exception as e:
            print(f"Error handling TCP client {address}: {e}")
        finally:
            self.clients.discard(connection)
            self.listener_count -= 1
            connection.close()
            print(f"TCP client disconnected: {address}")
    
    def process_audio_data(self, data, address):
        """Process received audio data"""
        if len(data) < 2:
            return
        
        sequence_number = int.from_bytes(data[:2], byteorder="little", signed=False)
        audio_data = data[2:]
        
        if self.expected_seq_num == sequence_number:
            # Play received audio
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Received Sequence #{sequence_number} ({len(data)} bytes) from {address}")
            try:
                self.play_stream.write(audio_data)
            except Exception as e:
                print(f"Error playing audio: {e}")
            
            self.expected_seq_num = (self.expected_seq_num + 1) % 65536
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Out of sequence #{sequence_number} (expected {self.expected_seq_num}) from {address}")
            # Play silence for missing packets
            try:
                self.play_stream.write(self.silence_data)
            except Exception as e:
                print(f"Error playing silence: {e}")
            
            if sequence_number > self.expected_seq_num:
                # Skip ahead to catch up
                self.expected_seq_num = (sequence_number + 1) % 65536
    
    def run_udp_server(self):
        """Run UDP server"""
        print("Starting UDP audio server...")
        while self.is_running:
            try:
                data, address = self.server_socket.recvfrom(self.CHUNK * self.NUMCHUNKS * 2 + 2)
                self.process_audio_data(data, address)
            except socket.error as e:
                if self.is_running:
                    print(f"UDP socket error: {e}")
                break
            except Exception as e:
                print(f"Unexpected error in UDP server: {e}")
    
    def run_tcp_server(self):
        """Run TCP server"""
        print("Starting TCP audio server...")
        while self.is_running:
            try:
                connection, address = self.server_socket.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_tcp_client,
                    args=(connection, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except socket.error as e:
                if self.is_running:
                    print(f"TCP socket error: {e}")
                break
            except Exception as e:
                print(f"Unexpected error in TCP server: {e}")
    
    def start(self):
        """Start the audio server"""
        self.is_running = True
        
        if self.protocol == 'udp':
            self.server_thread = threading.Thread(target=self.run_udp_server)
        else:
            self.server_thread = threading.Thread(target=self.run_tcp_server)
        
        self.server_thread.daemon = True
        self.server_thread.start()
        
        print(f"Audio server started on port {self.port}")
        print(f"Listening for {self.protocol.upper()} connections...")
        print(f"Current listeners: {self.listener_count}")
    
    def stop(self):
        """Stop the audio server"""
        print("Stopping audio server...")
        self.is_running = False
        
        # Close all TCP connections
        for client in self.clients.copy():
            try:
                client.close()
            except:
                pass
        
        # Close server socket
        if hasattr(self, 'server_socket'):
            self.server_socket.close()
        
        # Stop audio stream
        if hasattr(self, 'play_stream'):
            self.play_stream.stop_stream()
            self.play_stream.close()
        
        # Close PyAudio
        if hasattr(self, 'pyaudio_obj'):
            self.pyaudio_obj.terminate()
        
        print("Audio server stopped")

# Global server instance
audio_server = None

def signal_handler(signum, frame):
    """Handle interrupt signal"""
    global audio_server
    print("\nReceived interrupt signal...")
    if audio_server:
        audio_server.stop()
    sys.exit(0)

def main():
    global audio_server
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Audio Stream Server")
    parser.add_argument("--protocol", required=False, default='udp', 
                       choices=['udp', 'tcp'], help="Protocol to use")
    parser.add_argument("--port", required=False, default=12345, type=int,
                       help="Port to listen on")
    parser.add_argument("--size", required=False, default=10, type=int,
                       choices=range(10, 151, 10), help="Chunk size in milliseconds")
    
    args = parser.parse_args()
    
    try:
        # Create and start server
        audio_server = AudioServer(
            protocol=args.protocol,
            port=args.port,
            chunk_size=args.size
        )
        
        audio_server.start()
        
        # Keep server running
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if audio_server:
            audio_server.stop()

if __name__ == "__main__":
    main()