import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useRevokeOtherSessions, useRevokeSession, useSessions, type ActiveSession } from "@/services/accountService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

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
 * Perangkat yang sedang masuk + "Keluarkan" per perangkat dan "Keluarkan perangkat lain" (M1 / P1-7).
 * Token akses perangkat lain habis paling lama 15 menit.
 */
export function AccountSessionsPanel() {
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
        <section aria-label="Perangkat yang masuk">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <TextBlock as="h2" className="text-base font-semibold">Perangkat yang masuk</TextBlock>
            {others > 0 && (
              <ActionButton
                variant="outline"
                disabled={revokeOthers.isPending}
                onClick={() => run(() => revokeOthers.mutateAsync(), "Perangkat lain dikeluarkan (paling lambat 15 menit).")}
              >
                Keluarkan perangkat lain
              </ActionButton>
            )}
          </div>
          <div className="rounded-panel border border-line bg-surface shadow-card">
            {sessions.isPending && <LoadingBar className="m-4 h-10" />}
            {sessions.isError && <TextBlock className="px-5 py-4 text-sm text-danger">Daftar perangkat tidak dapat dimuat.</TextBlock>}
            <ListBlock className="divide-y divide-line">
              {sessions.data?.map((s) => (
                <ListEntry key={s.id} className="flex flex-col gap-2 px-5 py-3 text-sm md:flex-row md:items-center md:justify-between">
                  <div>
                    <TextBlock className="font-medium">
                      {deviceName(s)}
                      {s.current && <TextBlock as="span" className="ml-2 rounded-full bg-success-bg px-2 py-0.5 text-xs text-success">Perangkat ini</TextBlock>}
                    </TextBlock>
                    <TextBlock className="text-mist">
                      Masuk {s.issued_at ? formatDateTime(s.issued_at) : "-"}
                      {s.last_used_at && ` · terakhir aktif ${formatDateTime(s.last_used_at)}`}
                      {s.ip_address && ` · ${s.ip_address}`}
                    </TextBlock>
                  </div>
                  {!s.current && (
                    <ActionButton
                      size="sm"
                      variant="outline"
                      aria-label={`Keluarkan ${deviceName(s)}`}
                      disabled={revoke.isPending}
                      onClick={() => run(() => revoke.mutateAsync(s.id), "Perangkat dikeluarkan (paling lambat 15 menit).")}
                    >
                      Keluarkan
                    </ActionButton>
                  )}
                </ListEntry>
              ))}
            </ListBlock>
          </div>
          <TextBlock className="mt-2 text-body-sm text-mist">
            Perangkat yang dikeluarkan harus masuk lagi; akses yang sedang berjalan berakhir paling lama 15 menit.
          </TextBlock>
        </section>
  );
}
