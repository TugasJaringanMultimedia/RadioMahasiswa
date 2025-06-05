import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'audio_streaming',
    'user': 'root',
    'password': '',  # Default XAMPP password kosong
    'port': 3306
}

def get_database_connection():
    """Membuat koneksi ke database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def test_connection():
    """Test koneksi database"""
    conn = get_database_connection()
    if conn:
        print("Database connection successful!")
        conn.close()
        return True
    else:
        print("Database connection failed!")
        return False