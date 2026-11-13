import { toast } from "sonner";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { useFaceStatus } from "@/services/accountService";
import { Pill } from "@/components/molecules/Pill";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FACE_CONSENT_TEXT } from "@/lib/faceConsent";
import { formatDateTime } from "@/lib/format";

/**
 * Pengenalan wajah di halaman Akun: status pendaftaran; karyawan lapangan yang belum terdaftar mendaftar lewat kamera.
 * Daftar ulang hanya setelah HR mengatur ulang pendaftaran (server menolak pendaftaran kedua).
 */
export function FaceBiometricSection() {
  const faceStatus = useFaceStatus();

  if (faceStatus.isPending) {
    return (
      <section aria-label="Pengenalan wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
        <LoadingBar className="mb-2 h-6 w-48" />
        <LoadingBar className="h-16 w-full" />
      </section>
    );
  }
  if (faceStatus.isError) return null;
  const data = faceStatus.data;

  return (
    <section aria-label="Pengenalan wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <TextBlock as="h2" className="text-base font-semibold">Pengenalan Wajah</TextBlock>
          <TextBlock className="text-xs text-mist">Wajah Anda dipakai untuk memastikan yang absen adalah Anda, lewat aplikasi HP maupun web.</TextBlock>
        </div>
        {data.enrolled ? (
          <Pill tone="success">Wajah terdaftar</Pill>
        ) : data.required ? (
          <Pill tone="warning">Belum terdaftar</Pill>
        ) : (
          <Pill tone="neutral">Tidak diwajibkan</Pill>
        )}
      </div>

      {data.enrolled ? (
        <div className="space-y-1 rounded-lg border border-line bg-surface p-3 text-xs text-mist" data-testid="face-enroll-info">
          {data.enrolled_at && <TextBlock>{`Didaftarkan pada ${formatDateTime(data.enrolled_at)}`}</TextBlock>}
          <TextBlock>Ingin mendaftar ulang (misalnya ganti HP)? Minta HR mengatur ulang pendaftaran wajah Anda.</TextBlock>
        </div>
      ) : (
        <div className="rounded-lg border border-line bg-surface p-3.5">
          <TextBlock className="mb-3 text-sm text-mist">{FACE_CONSENT_TEXT}</TextBlock>
          <FaceEnrollCapture
            onEnrolled={() => {
              void faceStatus.refetch();
              toast.success("Wajah berhasil didaftarkan.");
            }}
          />
        </div>
      )}
    </section>
  );
}
