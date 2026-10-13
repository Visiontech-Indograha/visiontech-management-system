import React, { useRef, useState, useCallback } from "react";
import Webcam from "react-webcam";
import axios from "axios";

export default function App() {
  const webcamRef = useRef(null);
  const [mode, setMode] = useState("absensi"); 
  const [absensiStep, setAbsensiStep] = useState(1); // 1: Deteksi Wajah, 2: Buka Mulut
  const [nama, setNama] = useState("");
  const [pesan, setPesan] = useState("");
  const [loading, setLoading] = useState(false);

  // Konfigurasi resolusi 1:1
  const videoConstraints = {
    width: 720,
    height: 720,
    facingMode: "user",
  };

  // Fungsi mengambil gambar base64
  const captureFoto = useCallback(() => {
    return webcamRef.current.getScreenshot();
  }, [webcamRef]);

  const handleEnroll = async () => {
    if (!nama) return setPesan("❌ Masukkan nama Anda.");
    
    const imageBase64 = captureFoto();
    if (!imageBase64) return setPesan("❌ Gagal mengakses kamera.");

    setLoading(true);
    setPesan("Mendaftarkan wajah ke server Python...");

    try {
      const response = await axios.post("http://localhost:8000/api/enroll", {
        nama: nama,
        image_base64: imageBase64,
      });
      setPesan(`✅ Sukses: ${response.data.pesan}`);
      setNama(""); 
    } catch (error) {
      setPesan(`❌ Gagal: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const livenessIntervalRef = useRef(null);
  const [timeLeft, setTimeLeft] = useState(0);

  const [enrollStep, setEnrollStep] = useState(0);
  const [enrollEmbeddings, setEnrollEmbeddings] = useState([]);
  const enrollIntervalRef = useRef(null);

  const challenges = [
    { id: "depan", instruksi: "1/6 - Hadap lurus ke depan" },
    { id: "kiri", instruksi: "2/6 - Tengok sedikit ke KIRI" },
    { id: "kanan", instruksi: "3/6 - Tengok sedikit ke KANAN" },
    { id: "atas", instruksi: "4/6 - Mendongak sedikit ke ATAS" },
    { id: "buka_mulut", instruksi: "5/6 - BUKA MULUT Anda" },
    { id: "kedip", instruksi: "6/6 - KEDIPKAN mata Anda" }
  ];

  // Bersihkan interval jika komponen unmount atau berpindah mode
  React.useEffect(() => {
    return () => {
      if (livenessIntervalRef.current) clearInterval(livenessIntervalRef.current);
      if (enrollIntervalRef.current) clearInterval(enrollIntervalRef.current);
    };
  }, []);

  // --- LOGIKA PENDAFTARAN (ENROLLMENT) ---
  const handleStartEnroll = () => {
    if (!nama) return setPesan("❌ Masukkan nama Anda.");
    setEnrollStep(1);
    setEnrollEmbeddings([]);
    startEnrollPolling(1, []);
  };

  const startEnrollPolling = (currentStep, currentEmbeddings) => {
    let ticks = 30; // 30 detik tiap tantangan
    setTimeLeft(ticks);
    const challengeObj = challenges[currentStep - 1];
    setPesan(`Merekam... ${challengeObj.instruksi}`);

    if (enrollIntervalRef.current) clearInterval(enrollIntervalRef.current);

    enrollIntervalRef.current = setInterval(async () => {
      ticks -= 1;
      setTimeLeft(ticks);

      if (ticks <= 0) {
        clearInterval(enrollIntervalRef.current);
        setEnrollStep(0);
        setPesan("❌ Waktu habis. Anda gagal melakukan instruksi. Silakan ulangi dari awal.");
        return;
      }

      const imageBase64 = captureFoto();
      if (!imageBase64) return;

      try {
        const response = await axios.post("http://localhost:8000/api/challenge_check", {
          image_base64: imageBase64,
          challenge: challengeObj.id
        });

        if (response.data.status === "sukses") {
          clearInterval(enrollIntervalRef.current);
          const newEmbeddings = [...currentEmbeddings, response.data.embedding];
          
          if (currentStep < challenges.length) {
            // Lanjut ke tantangan berikutnya
            setEnrollStep(currentStep + 1);
            startEnrollPolling(currentStep + 1, newEmbeddings);
          } else {
            // Semua tantangan selesai, kirim ke server
            setEnrollStep(0);
            submitFinalEnroll(newEmbeddings);
          }
        }
      } catch (error) {
        // Abaikan jika status menunggu
      }
    }, 500); // Polling lebih cepat (500ms) untuk menangkap kedipan mata
  };

  const submitFinalEnroll = async (embeddings) => {
    setLoading(true);
    setPesan("Memproses dan menyimpan data wajah...");
    try {
      const response = await axios.post("http://localhost:8000/api/enroll", {
        nama: nama,
        embeddings: embeddings,
      });
      setPesan(`✅ Sukses: ${response.data.pesan}`);
      setNama(""); 
    } catch (error) {
      setPesan(`❌ Gagal: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // --- LOGIKA ABSENSI ---
  const [absensiChallenge, setAbsensiChallenge] = useState("");

  const startLivenessPolling = (challengeId) => {
    let ticks = 30; // 30 detik
    setTimeLeft(ticks);

    if (livenessIntervalRef.current) clearInterval(livenessIntervalRef.current);

    livenessIntervalRef.current = setInterval(async () => {
      ticks -= 1;
      setTimeLeft(ticks);

      if (ticks <= 0) {
        clearInterval(livenessIntervalRef.current);
        setAbsensiStep(1);
        setAbsensiChallenge("");
        setPesan("❌ Waktu habis. Anda gagal liveness. Silakan ulangi dari awal.");
        return;
      }

      const imageBase64 = captureFoto();
      if (!imageBase64) return;

      try {
        const response = await axios.post("http://localhost:8000/api/absensi", {
          image_base64: imageBase64,
          step: 2,
          challenge: challengeId
        });

        if (response.data.status === "sukses") {
          clearInterval(livenessIntervalRef.current);
          setAbsensiStep(1);
          setAbsensiChallenge("");
          setTimeLeft(0);
          setPesan(`✅ ${response.data.pesan} (Mirip: ${response.data.kemiripan})`);
        }
      } catch (error) {
        // Abaikan error saat polling
      }
    }, 1000); 
  };

  const handleAbsensi = async () => {
    const imageBase64 = captureFoto();
    if (!imageBase64) return setPesan("❌ Gagal mengakses kamera.");

    setLoading(true);
    setPesan("Mencocokkan wajah...");

    try {
      const response = await axios.post("http://localhost:8000/api/absensi", {
        image_base64: imageBase64,
        step: 1
      });

      if (response.data.status === "step2") {
        const randomChallengeId = ["kiri", "kanan", "atas", "buka_mulut", "kedip"][Math.floor(Math.random() * 5)];
        setAbsensiChallenge(randomChallengeId);
        setAbsensiStep(2);
        setPesan(`✅ Wajah Dikenali! Lakukan instruksi di layar.`);
        startLivenessPolling(randomChallengeId);
      }
    } catch (error) {
      setPesan(`❌ Gagal: ${error.response?.data?.detail || error.message}`);
      setAbsensiStep(1);
      setAbsensiChallenge("");
    } finally {
      setLoading(false);
    }
  };

  const getChallengeText = (cId) => {
    const c = challenges.find(x => x.id === cId);
    return c ? c.instruksi.replace(/^\d\/6 - /, '') : "";
  };

  return (
    <div style={{ maxWidth: "500px", margin: "40px auto", fontFamily: "sans-serif", textAlign: "center" }}>
      <h2>Sistem Absensi (Anti-Spoofing)</h2>
      
      <div style={{ marginBottom: "20px" }}>
        <button 
          onClick={() => { setMode("absensi"); setAbsensiStep(1); setAbsensiChallenge(""); setPesan(""); }}
          style={{ marginRight: "10px", padding: "10px", background: mode === "absensi" ? "#007BFF" : "#ccc", color: "#fff", border: "none", borderRadius: "5px" }}
        >
          Mode Absen
        </button>
        <button 
          onClick={() => { setMode("enroll"); setEnrollStep(0); setAbsensiStep(1); setAbsensiChallenge(""); setPesan(""); }}
          style={{ padding: "10px", background: mode === "enroll" ? "#28A745" : "#ccc", color: "#fff", border: "none", borderRadius: "5px" }}
        >
          Pendaftaran Baru
        </button>
      </div>

      {/* Frame Standar Wajah */}
      <div style={{ position: "relative", width: "100%", border: "2px solid #333", borderRadius: "10px", overflow: "hidden", marginBottom: "20px", backgroundColor: "#000" }}>
        <Webcam
          audio={false}
          mirrored={true}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          videoConstraints={videoConstraints}
          style={{ width: "100%", display: "block", opacity: (enrollStep > 0 || absensiStep === 2) && timeLeft < 3 ? 0.8 : 1 }}
        />
        
        {/* Overlay Oval Transparan untuk Panduan Posisi Wajah */}
        <div style={{
          position: "absolute",
          top: "15%",
          left: "25%",
          width: "50%",
          height: "70%",
          border: "4px dashed rgba(255, 255, 255, 0.8)",
          borderRadius: "50%",
          boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.4)",
          pointerEvents: "none"
        }}></div>

        {/* Text Peringatan di Dalam Kamera */}
        {(enrollStep > 0 || absensiStep === 2) && (
          <div style={{
            position: "absolute",
            bottom: "10%",
            left: "5%",
            right: "5%",
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            color: "#FFD700",
            padding: "10px",
            borderRadius: "8px",
            fontSize: "18px",
            fontWeight: "bold",
            pointerEvents: "none"
          }}>
            {enrollStep > 0 ? (
              <>
                Tantangan {enrollStep}/6: {challenges[enrollStep - 1].instruksi.replace(/^\d\/6 - /, '')} <br/>
                <span style={{ fontSize: "14px", color: "#fff" }}>Waktu: {timeLeft}s</span>
              </>
            ) : (
              <>
                Liveness: {getChallengeText(absensiChallenge)} <br/>
                <span style={{ fontSize: "14px", color: "#fff" }}>Waktu: {timeLeft}s</span>
              </>
            )}
          </div>
        )}
      </div>

      <div style={{ marginBottom: "20px" }}>
        {mode === "enroll" ? (
          <>
            {enrollStep === 0 ? (
              <>
                <input
                  type="text"
                  placeholder="Nama Lengkap"
                  value={nama}
                  onChange={(e) => setNama(e.target.value)}
                  style={{ padding: "10px", width: "80%", marginBottom: "10px" }}
                />
                <br />
                <button onClick={handleStartEnroll} disabled={loading} style={{ padding: "10px 20px" }}>
                  {loading ? "Memproses..." : "Mulai Pendaftaran Terstandarisasi"}
                </button>
              </>
            ) : (
              <div style={{ padding: "10px", color: "#28A745", fontWeight: "bold" }}>
                Sedang Merekam Wajah... (Lihat instruksi di dalam kamera)
              </div>
            )}
          </>
        ) : (
          <>
            {absensiStep === 2 ? (
              <div style={{ padding: "10px", color: "#ff9800", fontWeight: "bold" }}>
                Verifikasi Liveness Aktif... (Lihat instruksi di dalam kamera)
              </div>
            ) : (
              <button 
                 onClick={handleAbsensi} 
                 disabled={loading} 
                 style={{ 
                     padding: "10px 20px", 
                     background: "#007BFF",
                     color: "white", border: "none", borderRadius: "5px"
                 }}
              >
                {loading ? "Mendeteksi..." : "Mulai Absen"}
              </button>
            )}
          </>
        )}
      </div>

      {pesan && (
        <div style={{ padding: "15px", borderRadius: "5px", background: "#f4f4f4", border: "1px solid #ddd" }}>
          <strong>{pesan}</strong>
        </div>
      )}
    </div>
  );
}