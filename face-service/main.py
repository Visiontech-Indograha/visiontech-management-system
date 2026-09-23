# pyright: reportMissingImports=false
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from database import init_db, get_db_connection
from face_utils import get_face_embedding
from pgvector.psycopg2 import register_vector
from contextlib import asynccontextmanager

# Inisiasi tabel database saat server pertama kali dijalankan
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Face Recognition Microservice", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "face-service"}

@app.post("/register")
async def register_face(karyawan_id: str = Form(...), file: UploadFile = File(...)):
    """ Endpoint untuk menyimpan wajah baru ke database. """
    image_bytes = await file.read()
    embedding = get_face_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi. Pastikan foto terlihat jelas.")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Simpan ke DB. Jika karyawan_id sudah ada, perbarui data wajahnya (Upsert)
        cur.execute("""
            INSERT INTO face_encodings (karyawan_id, embedding) 
            VALUES (%s, %s) 
            ON CONFLICT (karyawan_id) 
            DO UPDATE SET embedding = EXCLUDED.embedding
        """, (karyawan_id, embedding.tolist()))
        
        return {"status": "success", "message": f"Data wajah karyawan {karyawan_id} berhasil disimpan."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/verify")
async def verify_face(file: UploadFile = File(...)):
    """ Endpoint untuk absensi/verifikasi kecocokan wajah. """
    image_bytes = await file.read()
    embedding = get_face_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada gambar.")

    conn = get_db_connection()
    register_vector(conn) # Wajib dipanggil untuk membaca tipe vector dari DB
    cur = conn.cursor()
    
    try:
        # Gunakan operator <-> dari pgvector untuk mencari Jarak Euclidean terdekat
        cur.execute("""
            SELECT karyawan_id, embedding <-> %s AS distance
            FROM face_encodings
            ORDER BY distance ASC
            LIMIT 1;
        """, (embedding.tolist(),))

        result = cur.fetchone()
        
        if result:
            karyawan_id, distance = result
            
            # Threshold bawaan dlib adalah 0.6. 
            # Jika jarak <= 0.5, kecocokannya sangat tinggi (sangat identik)
            if distance <= 0.5:
                return {
                    "match": True, 
                    "karyawan_id": karyawan_id, 
                    "distance": round(distance, 4),
                    "message": "Wajah berhasil dikenali."
                }
            else:
                return {
                    "match": False, 
                    "closest_distance": round(distance, 4),
                    "message": "Wajah tidak cocok dengan data manapun."
                }
        else:
            return {"match": False, "message": "Database wajah masih kosong."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()