import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

interface Point {
  lat: number;
  lng: number;
}

/**
 * Swafoto absen web (R-33): wajib bila di luar radius lokasi. Diambil langsung dari kamera perangkat
 * (bukan unggah berkas, agar tidak memakai foto lama), diberi watermark koordinat & waktu seperti di HP,
 * lalu diunggah ke POST /files/upload. Server tetap menolak absen di luar radius tanpa swafoto.
 */
export function SelfieCaptureDialog({
  info,
  position,
  siteName,
  onCancel,
  onCaptured,
}: {
  info: string;
  position: Point;
  siteName: string;
  onCancel: () => void;
  onCaptured: (fileId: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    if (!navigator.mediaDevices?.getUserMedia) {
      queueMicrotask(() => setCameraError("Browser ini tidak dapat membuka kamera. Gunakan browser lain."));
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then(async (s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        const video = videoRef.current;
        if (video) {
          video.srcObject = s;
          await video.play().catch(() => undefined);
          setReady(true);
        }
      })
      .catch((err: unknown) => {
        const denied = err instanceof DOMException && err.name === "NotAllowedError";
        setCameraError(
          denied
            ? "Akses kamera ditolak. Izinkan kamera untuk situs ini di pengaturan browser, lalu coba lagi."
            : "Kamera tidak ditemukan atau sedang dipakai aplikasi lain.",
        );
      });
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = async () => {
    const video = videoRef.current;
    if (!video) return;
    // Bingkai kosong/terlalu kecil (kamera belum siap) bukan bukti kehadiran — jangan diunggah.
    if (video.videoWidth < 160 || video.videoHeight < 120) {
      setUploadError("Gambar kamera belum siap. Tunggu sampai wajah terlihat, lalu ambil foto lagi.");
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("canvas");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      // Watermark: koordinat, waktu, lokasi — sama dengan swafoto HP.
      const lines = [
        `${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}`,
        new Date().toLocaleString("id-ID"),
        `${siteName} · Visiontech`,
      ];
      const size = Math.max(14, Math.round(canvas.width / 40));
      ctx.font = `${size}px monospace`;
      const pad = size * 0.6;
      const boxH = lines.length * size * 1.3 + pad * 2;
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      ctx.fillRect(0, canvas.height - boxH, canvas.width, boxH);
      ctx.fillStyle = "#ffffff";
      lines.forEach((line, i) => ctx.fillText(line, pad, canvas.height - boxH + pad + size * (i + 1) * 1.15));
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
      if (!blob) throw new Error("blob");
      const form = new FormData();
      form.append("file", blob, "swafoto-absen.jpg");
      const uploaded = (await api.post<{ file_id: string }>("/files/upload", form)).data;
      onCaptured(uploaded.file_id);
    } catch (err) {
      setUploadError(errorMessage(err, "Swafoto gagal disimpan. Coba lagi."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog
      open
      title="Swafoto absen"
      onClose={onCancel}
      footer={
        <>
          <Button variant="outline" onClick={onCancel} disabled={uploading}>
            Batal
          </Button>
          <Button onClick={capture} disabled={!ready || uploading}>
            {uploading ? "Menyimpan..." : "Ambil foto"}
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-mist">{info}</p>
      {cameraError ? (
        <p role="alert" className="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {cameraError}
        </p>
      ) : (
        <video
          ref={videoRef}
          muted
          playsInline
          aria-label="Pratinjau kamera"
          className="aspect-video w-full rounded-control bg-black object-cover"
        />
      )}
      {uploadError && (
        <p role="alert" className="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {uploadError}
        </p>
      )}
    </Dialog>
  );
}
