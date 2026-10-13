import { toast } from "sonner";
import { useSession } from "@/stores/sessionStore";
import { useFaceStatus, useSetFaceConsent, type FaceStatus } from "@/services/accountService";
import { errorMessage } from "@/lib/errors";
import { FaceEnrollRequiredTemplate } from "@/components/templates/face/FaceEnrollRequiredTemplate";

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
    <FaceEnrollRequiredTemplate
      granted={granted}
      policyText={status.policy.text}
      consentPending={setConsent.isPending}
      onGrant={grant}
      onEnrolled={() => void refetch()}
      onLogout={() => void logout()}
    />
  );
}
