import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { ROLE_LABEL } from "@/lib/types";
import { useRevokeOtherSessions, useRevokeSession, useSessions, type ActiveSession } from "./api";

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
