import psycopg2  # type: ignore[reportMissingModuleSource]
from importlib import import_module

# Sesuaikan dengan pengaturan database Docker Anda
DB_CONFIG = {
    "dbname": "facedb",
    "user": "postgres",
    "password": "Passebb123",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Aktifkan ekstensi pgvector
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Buat tabel untuk menyimpan ID karyawan dan 128 vektor wajah
    cur.execute("""
        CREATE TABLE IF NOT EXISTS face_encodings (
            id SERIAL PRIMARY KEY,
            karyawan_id VARCHAR(50) UNIQUE NOT NULL,
            embedding VECTOR(128)
        );
    """)
    
    # Daftarkan tipe vector ke psycopg2 agar Python mengerti tipe datanya
    register_vector = import_module("pgvector.psycopg2").register_vector
    register_vector(conn)
    cur.close()
    conn.close()