import { FaceConsentForm } from "@/components/organisms/face/FaceConsentForm";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { FaceEnrollIntro } from "@/components/organisms/face/FaceEnrollIntro";
import { FaceGateLogoutButton } from "@/components/organisms/face/FaceGateLogoutButton";

/** Kerangka layar penuh wajib daftar wajah: persetujuan biometrik → pendaftaran → tombol keluar. */
export function FaceEnrollRequiredTemplate({ granted, policyText, consentPending, onGrant, onEnrolled, onLogout }: {
  granted: boolean;
  policyText: string;
  consentPending: boolean;
  onGrant: () => void;
  onEnrolled: () => void;
  onLogout: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-4 py-8" data-testid="face-gate">
      <header className="text-center">
        <FaceEnrollIntro />
      </header>

      {!granted ? (
        <section className="space-y-3 rounded-panel border border-line bg-surface p-4 shadow-card">
          <FaceConsentForm policyText={policyText} pending={consentPending} onGrant={onGrant} />
        </section>
      ) : (
        <section className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <FaceEnrollCapture onEnrolled={onEnrolled} />
        </section>
      )}

      <div className="text-center">
        <FaceGateLogoutButton onLogout={onLogout} />
      </div>
    </main>
  );
}
