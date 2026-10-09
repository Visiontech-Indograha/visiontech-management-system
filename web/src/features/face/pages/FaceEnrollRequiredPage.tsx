import { toast } from "sonner";
import { useSession } from "@/app/session";
import { useFaceStatus, useSetFaceConsent, type FaceStatus } from "@/features/account/accountService";
import { errorMessage } from "@/lib/errors";
import { FaceConsentForm } from "../components/FaceConsentForm";
import { FaceEnrollCapture } from "../components/FaceEnrollCapture";
import { FaceEnrollIntro } from "../components/FaceEnrollIntro";
import { FaceGateLogoutButton } from "../components/FaceGateLogoutButton";

/** Layar penuh yang menggantikan semua halaman sampai wajah akun ini terdaftar (status.enrollment_required). */
export function FaceEnrollRequiredPage({ status }: { status: FaceStatus }) {
  const { logout } = useSession();
  const { refetch } = useFaceStatus();
  const setConsent = useSetFaceConsent();
  const granted = status.consent === "GRANTED";

  const grant = async () => {
    try {
      await setConsent.mutateAsync({ state: "GRANTED", policy_version: status.policy.version });
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-4 py-8" data-testid="face-gate">
      <header className="text-center">
        <FaceEnrollIntro />
      </header>

      {!granted ? (
        <section className="space-y-3 rounded-panel border border-line bg-surface p-4 shadow-card">
          <FaceConsentForm policyText={status.policy.text} pending={setConsent.isPending} onGrant={grant} />
        </section>
      ) : (
        <section className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <FaceEnrollCapture onEnrolled={() => void refetch()} />
        </section>
      )}

      <div className="text-center">
        <FaceGateLogoutButton onLogout={() => void logout()} />
      </div>
    </main>
  );
}
