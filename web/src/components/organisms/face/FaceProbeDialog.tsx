import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { FaceCamera, type FaceLiveness } from "./FaceCamera";
import { ActionButton } from "@/components/molecules/ActionButton";
import { probeFace } from "@/services/faceService";

/**
 * Verifikasi wajah untuk absen web (pekerja kantor; web tidak punya jalur luring). Mengunggah gambar wajah sementara
 * (`/face/probe`) dan mengembalikan `probe_id` untuk dikirim bersama absen; server yang memutuskan cocok atau tidak.
 * Face-service mati (503) → absen tetap boleh lanjut tanpa probe (server menandainya untuk diperiksa).
 */
export function FaceProbeDialog({
  title,
  onCancel,
  onDone,
}: {
  title: string;
  onCancel: () => void;
  onDone: (probeId: string | null) => void;
}) {
  const probe = async (photos: Blob[], liveness: FaceLiveness) => {
    const form = new FormData();
    form.append("file", photos[0]!, "wajah.jpg");
    form.append("liveness", JSON.stringify(liveness));
    try {
      onDone(await probeFace(form));
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        toast.warning("Pemeriksaan wajah sedang tidak tersedia. Absen tetap dicatat dan akan diperiksa.");
        onDone(null);
        return;
      }
      throw e;
    }
  };

  return (
    <VmsDialog
      open
      title={title}
      onClose={onCancel}
      footer={
        <ActionButton variant="outline" onClick={onCancel}>
          Batal
        </ActionButton>
      }
    >
      <FaceCamera
        poses={["Hadap lurus ke kamera"]}
        startLabel="Mulai Verifikasi Wajah"
        doneMessage="Wajah terverifikasi."
        onCaptured={probe}
      />
    </VmsDialog>
  );
}
