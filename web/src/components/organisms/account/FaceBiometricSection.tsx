import { useState } from "react";
import { toast } from "sonner";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { errorMessage } from "@/lib/errors";
import { useFaceStatus, useSetFaceConsent } from "@/services/accountService";
import { Pill } from "@/components/molecules/Pill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlLabel } from "@/components/molecules/FormBlock";

/** Biometrik wajah di halaman Akun: status, persetujuan (beri/tarik), pendaftaran/daftar ulang lewat webcam. */
export function FaceBiometricSection() {
  const faceStatus = useFaceStatus();
  const setConsent = useSetFaceConsent();

  const [agreed, setAgreed] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  if (faceStatus.isPending) {
    return (
      <section aria-label="Biometrik Wajah" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
        <LoadingBar className="mb-2 h-6 w-48" />
        <LoadingBar className="h-16 w-full" />
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
        <TextBlock as="h2" className="text-base font-semibold">Biometrik Wajah</TextBlock>
        <TextBlock className="mt-2 text-sm text-mist">
          Fitur pendaftaran biometrik wajah hanya tersedia untuk akun yang terhubung dengan data karyawan.
        </TextBlock>
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
          <TextBlock as="h2" className="text-base font-semibold">Biometrik Wajah (Face Recognition)</TextBlock>
          <TextBlock className="text-xs text-mist">Verifikasi kehadiran server-side berbasis pencocokan fitur wajah.</TextBlock>
        </div>
        {data.enrolled ? (
          <Pill tone="success">Wajah Terdaftar</Pill>
        ) : isConsentGiven ? (
          <Pill tone="warning">Belum Terdaftar</Pill>
        ) : (
          <Pill tone="neutral">Belum Persetujuan</Pill>
        )}
      </div>

      {/* Box Persetujuan Kebijakan */}
      <div className="mb-4 rounded-lg border border-line/60 bg-muted/20 p-3.5 text-sm">
        <div className="mb-2 flex items-center justify-between">
          <TextBlock as="span" className="font-medium text-foreground">Persetujuan Pemrosesan Biometrik</TextBlock>
          {isConsentGiven ? (
            <Pill tone="success">{`Disetujui (v${data.consent_policy_version ?? data.policy.version})`}</Pill>
          ) : (
            <Pill tone="danger">Belum Disetujui</Pill>
          )}
        </div>

        {!isConsentGiven ? (
          <div className="mt-2 space-y-3">
            <TextBlock className="rounded border border-line bg-surface p-2.5 text-xs leading-relaxed text-mist">
              {data.policy.text}
            </TextBlock>
            <div className="flex items-center gap-2">
              <CheckControl
                id="consent-agree"
                checked={agreed}
                onCheckedChange={(c) => setAgreed(!!c)}
              />
              <ControlLabel htmlFor="consent-agree" className="cursor-pointer text-xs text-foreground">
                Saya menyetujui pemrosesan data biometrik wajah untuk verifikasi kehadiran.
              </ControlLabel>
            </div>
            <ActionButton
              size="sm"
              disabled={!agreed || setConsent.isPending}
              onClick={() => handleToggleConsent(true)}
            >
              {setConsent.isPending ? "Menyimpan..." : "Beri Persetujuan Biometrik"}
            </ActionButton>
          </div>
        ) : (
          <div className="mt-2 flex items-center justify-between text-xs text-mist">
            <TextBlock as="span">Persetujuan aktif. Template biometrik disimpan aman di server.</TextBlock>
            <ActionButton
              size="sm"
              variant="outline"
              className="text-danger hover:text-danger"
              disabled={setConsent.isPending}
              onClick={() => handleToggleConsent(false)}
            >
              Tarik Persetujuan
            </ActionButton>
          </div>
        )}
      </div>

      {/* Pendaftaran lewat webcam: dua gerakan acak diperiksa server (bukan pilih berkas dari disk). */}
      {isConsentGiven && (
        <div className="space-y-3" data-testid="face-enroll-info">
          <div className="flex items-center justify-between">
            <TextBlock as="h3" className="text-sm font-medium">Pendaftaran Wajah</TextBlock>
            {data.enrolled && !enrolling && (
              <ActionButton size="sm" variant="outline" onClick={() => setEnrolling(true)}>
                Daftar Ulang Wajah
              </ActionButton>
            )}
          </div>
          {data.enrolled && !enrolling ? (
            <div className="space-y-1 rounded-lg border border-line bg-surface p-3 text-xs text-mist">
              <TextBlock>Model Biometrik: <TextBlock as="span" className="font-mono text-foreground">{data.model_name ?? "InsightFace buffalo_s"}</TextBlock></TextBlock>
              <TextBlock>Masa Berlaku Template: <TextBlock as="span" className="text-foreground">{`${data.template_ttl_days} hari`}</TextBlock></TextBlock>
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
