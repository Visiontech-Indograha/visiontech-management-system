import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import getpass

def setup_database():
    print("=== Setup Database Absensi Wajah ===")
    pg_password = getpass.getpass("Masukkan password untuk user 'postgres': ")
    
    # 1. Connect ke postgres untuk membuat database baru
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password=pg_password,
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Cek apakah database sudah ada
        cur.execute("SELECT 1 FROM pg_database WHERE datname='absensi_wajah'")
        if not cur.fetchone():
            print("Membuat database 'absensi_wajah'...")
            cur.execute("CREATE DATABASE absensi_wajah")
        else:
            print("Database 'absensi_wajah' sudah ada.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"\nGagal login ke PostgreSQL. Pastikan password benar! Error: {type(e).__name__}")
        return

    # 2. Connect ke absensi_wajah untuk setup tabel & pgvector
    try:
        conn2 = psycopg2.connect(
            dbname="absensi_wajah",
            user="postgres",
            password=pg_password,
            host="localhost",
            port="5432"
        )
        conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur2 = conn2.cursor()
        
        print("Mengaktifkan ekstensi 'vector'...")
        cur2.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        print("Membuat tabel 'karyawan'...")
        cur2.execute("""
            CREATE TABLE IF NOT EXISTS karyawan (
                id SERIAL PRIMARY KEY,
                nama VARCHAR(255) NOT NULL,
                face_embedding vector(512)
            )
        """)
        
        cur2.close()
        conn2.close()
        print("\n✅ Setup Database Selesai!")
        
    except Exception as e:
        print(f"\nGagal setup tabel: {e}")

if __name__ == "__main__":
    setup_database()
 