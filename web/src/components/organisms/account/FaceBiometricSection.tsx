import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { Checkbox } from "@/components/atoms/Checkbox";
import { Skeleton } from "@/components/atoms/Skeleton";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { errorMessage } from "@/lib/errors";
import { useFaceStatus, useSetFaceConsent } from "@/services/accountService";

/** Biometrik wajah di halaman Akun: status, persetujuan (beri/tarik), pendaftaran/daftar ulang lewat webcam. */
export function FaceBiometricSection() {
  const faceStatus = useFaceStatus();
  const setConsent = useSetFaceConsent();

  const [agreed, setAgreed] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  if (faceStatus.isPending) {
    return (
      <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
        <Skeleton className="mb-2 h-6 w-48" />
        <Skeleton className="h-16 w-full" />
      </section>
    );
  }

  if (faceStatus.isError) {
    return null;
  }

  const data = faceStatus.data;
  if (!data?.employee_linked) {
    return (
      <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
        <h2 className="text-base font-semibold">Biometrik Wajah</h2>
        <p className="mt-2 text-sm text-mist">
          Fitur pendaftaran biometrik wajah hanya tersedia untuk akun yang terhubung dengan data karyawan.
        </p>
      </section>
    );
  }

  const isConsentGiven = data.consent === "GRANTED";

  const handleToggleConsent = async (grant: boolean) => {
    try {
      await setConsent.mutateAsync({
        state: grant ? "GRANTED" : "WITHDRAWN",
        policy_version: data.policy.version,
      });
      toast.success(grant ? "Persetujuan biometrik berhasil dicatat." : "Persetujuan biometrik berhasil ditarik.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">Biometrik Wajah (Face Recognition)</h2>
          <p className="text-xs text-mist">Verifikasi kehadiran server-side berbasis pencocokan fitur wajah.</p>
        </div>
        {data.enrolled ? (
          <Badge tone="success">Wajah Terdaftar</Badge>
        ) : isConsentGiven ? (
          <Badge tone="warning">Belum Terdaftar</Badge>
        ) : (
          <Badge tone="neutral">Belum Persetujuan</Badge>
        )}
      </div>

      {/* Box Persetujuan Kebijakan */}
      <div className="mb-4 rounded-lg border border-line/60 bg-muted/20 p-3.5 text-sm">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-medium text-foreground">Persetujuan Pemrosesan Biometrik</span>
          {isConsentGiven ? (
            <Badge tone="success">{`Disetujui (v${data.consent_policy_version ?? data.policy.version})`}</Badge>
          ) : (
            <Badge tone="danger">Belum Disetujui</Badge>
          )}
        </div>

        {!isConsentGiven ? (
          <div className="mt-2 space-y-3">
            <p className="rounded border border-line bg-surface p-2.5 text-xs leading-relaxed text-mist">
              {data.policy.text}
            </p>
            <div className="flex items-center gap-2">
              <Checkbox
                id="consent-agree"
                checked={agreed}
                onCheckedChange={(c) => setAgreed(!!c)}
              />
              <label htmlFor="consent-agree" className="cursor-pointer text-xs text-foreground">
                Saya menyetujui pemrosesan data biometrik wajah untuk verifikasi kehadiran.
              </label>
            </div>
            <Button
              size="sm"
              disabled={!agreed || setConsent.isPending}
              onClick={() => handleToggleConsent(true)}
            >
              {setConsent.isPending ? "Menyimpan..." : "Beri Persetujuan Biometrik"}
            </Button>
          </div>
        ) : (
          <div className="mt-2 flex items-center justify-between text-xs text-mist">
            <span>Persetujuan aktif. Template biometrik disimpan aman di server.</span>
            <Button
              size="sm"
              variant="outline"
              className="text-danger hover:text-danger"
              disabled={setConsent.isPending}
              onClick={() => handleToggleConsent(false)}
            >
              Tarik Persetujuan
            </Button>
          </div>
        )}
      </div>

      {/* Pendaftaran lewat webcam: dua gerakan acak diperiksa server (bukan pilih berkas dari disk). */}
      {isConsentGiven && (
        <div className="space-y-3" data-testid="face-enroll-info">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Pendaftaran Wajah</h3>
            {data.enrolled && !enrolling && (
              <Button size="sm" variant="outline" onClick={() => setEnrolling(true)}>
                Daftar Ulang Wajah
              </Button>
            )}
          </div>
          {data.enrolled && !enrolling ? (
            <div className="space-y-1 rounded-lg border border-line bg-surface p-3 text-xs text-mist">
              <p>Model Biometrik: <span className="font-mono text-foreground">{data.model_name ?? "InsightFace buffalo_s"}</span></p>
              <p>Masa Berlaku Template: <span className="text-foreground">{`${data.template_ttl_days} hari`}</span></p>
            </div>
          ) : (
            <div className="rounded-lg border border-line bg-surface p-3.5">
              <FaceEnrollCapture
                onEnrolled={() => {
                  setEnrolling(false);
                  void faceStatus.refetch();
                  toast.success("Wajah berhasil didaftarkan.");
                }}
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
