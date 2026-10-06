import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { FaceEnrollCapture } from "@/features/face/FaceEnrollCapture";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { ROLE_LABEL } from "@/lib/types";
import {
  useFaceStatus,
  useRevokeOtherSessions,
  useRevokeSession,
  useSessions,
  useSetFaceConsent,
  type ActiveSession,
} from "./api";

/** Nama perangkat yang bisa dikenali orang awam dari user-agent. */
function deviceName(s: ActiveSession): string {
  const ua = s.user_agent ?? "";
  const os = /Android/i.test(ua) ? "Android" : /iPhone|iPad/i.test(ua) ? "iPhone/iPad" : /Windows/i.test(ua) ? "Windows"
    : /Mac OS/i.test(ua) ? "Mac" : /Linux/i.test(ua) ? "Linux" : null;
  const app = /Dart|okhttp/i.test(ua) ? "Aplikasi Visiontech" : /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome"
    : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : null;
  const label = [app, os].filter(Boolean).join(" · ");
  return label || s.device_label || ua || "Perangkat tidak dikenal";
}

function FaceSection() {
  const faceStatus = useFaceStatus();
  const setConsent = useSetFaceConsent();

  const [agreed, setAgreed] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  if (faceStatus.isPending) {
    return (
      <section aria-label="Biometrik Wajah" className="mb-6 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-4">
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
      <section aria-label="Biometrik Wajah" className="mb-6 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-4">
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
    <section aria-label="Biometrik Wajah" className="mb-6 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-4">
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

/**
 * Akun & keamanan (M1 / P1-7): ganti password dan perangkat yang sedang masuk, termasuk
 * "Keluarkan perangkat lain". Token akses perangkat lain habis paling lama 15 menit.
 */
export function AccountPage() {
  const { me } = useSession();
  const sessions = useSessions();
  const revoke = useRevokeSession();
  const revokeOthers = useRevokeOtherSessions();
  const others = sessions.data?.filter((s) => !s.current).length ?? 0;

  const run = async (action: () => Promise<unknown>, done: string) => {
    try {
      await action();
      toast.success(done);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <>
      <PageHeader title="Akun & keamanan" />
      <section aria-label="Akun" className="mb-6 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-4">
        <p className="font-medium">{me?.email}</p>
        <p className="mb-4 text-sm text-mist">{me ? (ROLE_LABEL[me.role] ?? me.role) : ""}</p>
        <Button asChild variant="outline">
          <Link to="/change-password">Ganti password</Link>
        </Button>
      </section>

      <FaceSection />

      <section aria-label="Perangkat yang masuk" className="max-w-xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold">Perangkat yang masuk</h2>
          {others > 0 && (
            <Button
              variant="outline"
              disabled={revokeOthers.isPending}
              onClick={() => run(() => revokeOthers.mutateAsync(), "Perangkat lain dikeluarkan (paling lambat 15 menit).")}
            >
              Keluarkan perangkat lain
            </Button>
          )}
        </div>
        <div className="rounded-panel border border-line bg-surface shadow-card">
          {sessions.isPending && <Skeleton className="m-4 h-10" />}
          {sessions.isError && <p className="px-5 py-4 text-sm text-danger">Daftar perangkat tidak dapat dimuat.</p>}
          <ul className="divide-y divide-line">
            {sessions.data?.map((s) => (
              <li key={s.id} className="flex flex-col gap-2 px-5 py-3 text-sm md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-medium">
                    {deviceName(s)}
                    {s.current && <span className="ml-2 rounded-full bg-success-bg px-2 py-0.5 text-xs text-success">Perangkat ini</span>}
                  </p>
                  <p className="text-mist">
                    Masuk {s.issued_at ? formatDateTime(s.issued_at) : "-"}
                    {s.last_used_at && ` · terakhir aktif ${formatDateTime(s.last_used_at)}`}
                    {s.ip_address && ` · ${s.ip_address}`}
                  </p>
                </div>
                {!s.current && (
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label={`Keluarkan ${deviceName(s)}`}
                    disabled={revoke.isPending}
                    onClick={() => run(() => revoke.mutateAsync(s.id), "Perangkat dikeluarkan (paling lambat 15 menit).")}
                  >
                    Keluarkan
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-2 text-body-sm text-mist">
          Perangkat yang dikeluarkan harus masuk lagi; akses yang sedang berjalan berakhir paling lama 15 menit.
        </p>
      </section>
    </>
  );
}
