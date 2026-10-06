import { api } from "@/lib/api";
import { FaceCamera, type FaceLiveness } from "./FaceCamera";

const POSES = ["Hadap lurus ke kamera", "Tengok sedikit ke kiri", "Tengok sedikit ke kanan", "Tersenyum ke kamera"];

/** Pendaftaran wajah lewat webcam (bukan pilih berkas): dua gerakan acak yang diperiksa SERVER, lalu beberapa pose. */
export function FaceEnrollCapture({ onEnrolled }: { onEnrolled: () => void }) {
  const enroll = async (photos: Blob[], liveness: FaceLiveness) => {
    const form = new FormData();
    photos.forEach((p, i) => form.append("files", p, `pose${i}.jpg`));
    form.append("liveness", JSON.stringify(liveness));
    await api.post("/face/enroll", form);
    onEnrolled();
  };
  return (
    <FaceCamera
      poses={POSES}
      startLabel="Mulai Pendaftaran Wajah"
      doneMessage="Wajah berhasil didaftarkan."
      onCaptured={enroll}
    />
  );
}
