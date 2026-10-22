import { FaceCamera } from "./FaceCamera";
import { enrollFace } from "@/services/faceService";

const POSES = ["Hadap lurus ke kamera", "Tengok sedikit ke kiri", "Tengok sedikit ke kanan", "Tersenyum ke kamera"];

/** Pendaftaran wajah lewat webcam (bukan pilih berkas): beberapa pose; server menolak bila bukan satu orang yang sama. */
export function FaceEnrollCapture({ onEnrolled }: { onEnrolled: () => void }) {
  const enroll = async (photos: Blob[]) => {
    const form = new FormData();
    photos.forEach((p, i) => form.append("files", p, `pose${i}.jpg`));
    await enrollFace(form);
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
