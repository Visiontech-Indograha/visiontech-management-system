import { useState } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Button } from "@/components/atoms/Button";
import { Checkbox } from "@/components/atoms/Checkbox";
import { useFaceStatus, useSetFaceConsent, type FaceStatus } from "@/features/account/api";
import { errorMessage } from "@/lib/errors";
import { FaceEnrollCapture } from "./FaceEnrollCapture";

/** Layar penuh yang menggantikan semua halaman sampai wajah akun ini terdaftar (status.enrollment_required). */
export function FaceEnrollRequiredPage({ status }: { status: FaceStatus }) {
  const { logout } = useSession();
  const { refetch } = useFaceStatus();
  const setConsent = useSetFaceConsent();
  const [agreed, setAgreed] = useState(false);
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
        <h1 className="text-xl font-semibold">Daftarkan wajah Anda</h1>
        <p className="mt-1 text-sm text-mist">
          Pendaftaran wajah wajib dilakukan sekali sebelum Anda dapat membuka menu lainnya.
        </p>
      </header>

      {!granted ? (
        <section className="space-y-3 rounded-panel border border-line bg-surface p-4 shadow-card">
          <h2 className="text-sm font-medium">Persetujuan Pemrosesan Biometrik</h2>
          <p className="rounded border border-line bg-surface p-2.5 text-xs leading-relaxed text-mist">
            {status.policy.text}
          </p>
          <div className="flex items-center gap-2">
            <Checkbox id="gate-consent" checked={agreed} onCheckedChange={(c) => setAgreed(!!c)} />
            <label htmlFor="gate-consent" className="cursor-pointer text-xs">
              Saya menyetujui pemrosesan data biometrik wajah untuk verifikasi kehadiran.
            </label>
          </div>
          <Button disabled={!agreed || setConsent.isPending} onClick={grant}>
            {setConsent.isPending ? "Menyimpan..." : "Setuju dan Lanjut"}
          </Button>
        </section>
      ) : (
        <section className="rounded-panel border border-line bg-surface p-4 shadow-card">
          <FaceEnrollCapture onEnrolled={() => void refetch()} />
        </section>
      )}

      <div className="text-center">
        <Button variant="ghost" size="sm" onClick={() => void logout()}>
          Keluar
        </Button>
      </div>
    </main>
  );
}
