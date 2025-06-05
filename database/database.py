import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from .config import get_database_connection

class AudioFileDatabase:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        self.connection = get_database_connection()
        return self.connection is not None
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def add_audio_file(self, nama_file, rating, file_path=None, file_size=None, duration_seconds=None):
        """Menambah file audio baru ke database"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO audio_files (nama_file, rating, file_path, file_size, duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (nama_file, rating, file_path, file_size, duration_seconds)
            
            cursor.execute(query, values)
            self.connection.commit()
            
            print(f"Audio file '{nama_file}' added successfully with ID: {cursor.lastrowid}")
            return cursor.lastrowid
            
        except Error as e:
            print(f"Error adding audio file: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_files_by_name(self, nama_file_pattern):
        """Filter file berdasarkan nama (mendukung LIKE pattern)"""
        if not self.connect():
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM audio_files WHERE nama_file LIKE %s ORDER BY nama_file"
            cursor.execute(query, (f"%{nama_file_pattern}%",))
            
            results = cursor.fetchall()
            return results
            
        except Error as e:
            print(f"Error fetching files by name: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def get_files_by_rating(self, min_rating=None, max_rating=None):
        """Filter file berdasarkan rating"""
        if not self.connect():
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if min_rating is not None and max_rating is not None:
                query = "SELECT * FROM audio_files WHERE rating BETWEEN %s AND %s ORDER BY rating DESC"
                cursor.execute(query, (min_rating, max_rating))
            elif min_rating is not None:
                query = "SELECT * FROM audio_files WHERE rating >= %s ORDER BY rating DESC"
                cursor.execute(query, (min_rating,))
            elif max_rating is not None:
                query = "SELECT * FROM audio_files WHERE rating <= %s ORDER BY rating DESC"
                cursor.execute(query, (max_rating,))
            else:
                query = "SELECT * FROM audio_files ORDER BY rating DESC"
                cursor.execute(query)
            
            results = cursor.fetchall()
            return results
            
        except Error as e:
            print(f"Error fetching files by rating: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def get_all_files(self):
        """Mendapatkan semua file audio"""
        if not self.connect():
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM audio_files ORDER BY created_at DESC"
            cursor.execute(query)
            
            results = cursor.fetchall()
            return results
            
        except Error as e:
            print(f"Error fetching all files: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def update_rating(self, file_id, new_rating):
        """Update rating file audio"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            query = "UPDATE audio_files SET rating = %s WHERE id = %s"
            cursor.execute(query, (new_rating, file_id))
            self.connection.commit()
            
            return cursor.rowcount > 0
            
        except Error as e:
            print(f"Error updating rating: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def delete_file(self, file_id):
        """Hapus file dari database"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM audio_files WHERE id = %s"
            cursor.execute(query, (file_id,))
            self.connection.commit()
            
            return cursor.rowcount > 0
            
        except Error as e:
            print(f"Error deleting file: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()