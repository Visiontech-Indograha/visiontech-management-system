import { toast } from "sonner";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { useFaceStatus } from "@/services/accountService";
import { Pill } from "@/components/molecules/Pill";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDateTime } from "@/lib/format";

/**
 * Wajah di halaman Akun (wajah V2): status pendaftaran; pekerja lapangan yang belum terdaftar mendaftar lewat webcam.
 * Daftar ulang hanya setelah HR mengatur ulang pendaftaran (server menolak pendaftaran kedua).
 */
export function FaceBiometricSection() {
  const faceStatus = useFaceStatus();

  if (faceStatus.isPending) {
    return (
      <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
        <LoadingBar className="mb-2 h-6 w-48" />
        <LoadingBar className="h-16 w-full" />
      </section>
    );
  }
  if (faceStatus.isError) return null;
  const data = faceStatus.data;

  return (
    <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <TextBlock as="h2" className="text-base font-semibold">Biometrik Wajah</TextBlock>
          <TextBlock className="text-xs text-mist">Swafoto absen dicocokkan server dengan wajah terdaftar.</TextBlock>
        </div>
        {data.enrolled ? <Pill tone="success">Wajah Terdaftar</Pill> : <Pill tone="warning">Belum Terdaftar</Pill>}
      </div>

      {data.enrolled ? (
        <div className="space-y-1 rounded-lg border border-line bg-surface p-3 text-xs text-mist" data-testid="face-enroll-info">
          {data.enrolled_at && <TextBlock>{`Terdaftar: ${formatDateTime(data.enrolled_at)}`}</TextBlock>}
          {data.model_name && <TextBlock>{`Model: ${data.model_name}`}</TextBlock>}
          <TextBlock>Perlu mendaftar ulang (ganti wajah/HP)? Minta HR mengatur ulang pendaftaran wajah Anda.</TextBlock>
        </div>
      ) : data.required ? (
        <div className="rounded-lg border border-line bg-surface p-3.5">
          <FaceEnrollCapture
            onEnrolled={() => {
              void faceStatus.refetch();
              toast.success("Wajah berhasil didaftarkan.");
            }}
          />
        </div>
      ) : (
        <TextBlock className="text-sm text-mist">Pendaftaran wajah hanya untuk pekerja lapangan (absen lewat aplikasi HP).</TextBlock>
      )}
    </section>
  );
}
