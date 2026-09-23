from importlib import import_module

# Load the optional dependency without requiring the editor to resolve its module
# during static analysis. Install it in the active environment to use this API.
face_recognition = import_module("face_recognition")
cv2 = import_module("cv2")
np = import_module("numpy")

def get_face_embedding(image_bytes):
    # Ubah byte stream dari request HTTP menjadi array numpy
    nparr = np.frombuffer(image_bytes, np.uint8)
    
    # Decode menjadi format gambar yang dikenali OpenCV
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return None

    # OpenCV menggunakan format BGR, sedangkan AI dlib menggunakan format RGB
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Cari lokasi kotak wajah di dalam gambar
    face_locations = face_recognition.face_locations(rgb_img)
    
    # Jika tidak ada wajah sama sekali, gagalkan
    if not face_locations:
        return None

    # Ekstrak 128-dimensi vektor wajah
    # Kita ambil wajah pertama (index 0) yang terdeteksi
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
    
    if len(face_encodings) == 0:
        return None
        
    return face_encodings[0]