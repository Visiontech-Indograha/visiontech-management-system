import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { api, ApiError } from "@/lib/api";
import { FaceCamera, type FaceLiveness } from "./FaceCamera";

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
      const res = (await api.post<{ probe_id: string }>("/face/probe", form)).data;
      onDone(res.probe_id);
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
    <Dialog
      open
      title={title}
      onClose={onCancel}
      footer={
        <Button variant="outline" onClick={onCancel}>
          Batal
        </Button>
      }
    >
      <FaceCamera
        poses={["Hadap lurus ke kamera"]}
        startLabel="Mulai Verifikasi Wajah"
        doneMessage="Wajah terverifikasi."
        onCaptured={probe}
      />
    </Dialog>
  );
}
