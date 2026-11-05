import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import {
  DEVICE_SLOTS,
  useAccountAction,
  useAccountSessions,
  type AccountAction,
} from "@/services/employeeService";

/**
 * Perangkat yang sedang masuk dengan akun karyawan (HR/admin). Satu akun hanya boleh aktif di
 * {@link DEVICE_SLOTS} perangkat; "Keluarkan" menghentikan satu perangkat, tombol lain menghentikan semuanya.
 */
export function AccountDevicesAdmin({ employeeId }: { employeeId: string }) {
  const sessions = useAccountSessions(employeeId);
  const action = useAccountAction(employeeId);
  const [error, setError] = useState<string | null>(null);
  const rows = sessions.data ?? [];

  const run = async (a: AccountAction, done: string) => {
    setError(null);
    try {
      await action.mutateAsync(a);
      toast.success(done);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-3" aria-label="Perangkat yang masuk">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TextBlock className="font-medium">Perangkat yang masuk</TextBlock>
        {sessions.isSuccess && (
          <Pill tone={rows.length >= DEVICE_SLOTS ? "warning" : "neutral"} data-testid="device-slots">
            {`${rows.length} dari ${DEVICE_SLOTS} perangkat terpakai`}
          </Pill>
        )}
      </div>
      {sessions.isPending && <LoadingBar className="h-10 w-full" />}
      {sessions.isError && <TextBlock className="text-danger">Daftar perangkat tidak dapat dimuat.</TextBlock>}
      {sessions.isSuccess && rows.length === 0 && (
        <TextBlock className="text-mist">Belum ada perangkat yang masuk dengan akun ini.</TextBlock>
      )}
      {rows.length > 0 && (
        <ListBlock className="divide-y divide-line rounded-control border border-line">
          {rows.map((s) => (
            <ListEntry key={s.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <div className="min-w-0">
                <TextBlock className="truncate font-medium">{s.device_label ?? "Perangkat tanpa nama"}</TextBlock>
                <TextBlock className="text-xs text-mist">
                  {`Terakhir dipakai: ${s.last_used_at ? formatDateTime(s.last_used_at) : "belum diketahui"}`}
                  {s.ip_address ? ` · ${s.ip_address}` : ""}
                </TextBlock>
              </div>
              <ActionButton
                variant="outline"
                disabled={action.isPending}
                onClick={() => run({ kind: "revoke-session", sessionId: s.id }, "Perangkat dikeluarkan.")}
              >
                Keluarkan
              </ActionButton>
            </ListEntry>
          ))}
        </ListBlock>
      )}
      <FormErrorText message={error} className="mb-0" />
      <div className="flex flex-wrap gap-2">
        <ActionButton
          variant="outline"
          disabled={action.isPending || rows.length === 0}
          onClick={() => run({ kind: "revoke-all-sessions" }, "Semua perangkat dikeluarkan.")}
        >
          Keluarkan semua perangkat
        </ActionButton>
        <ActionButton
          variant="outline"
          disabled={action.isPending || rows.length === 0}
          onClick={() => run({ kind: "reset-device-slots" }, "Slot perangkat dikosongkan.")}
        >
          Kosongkan slot perangkat
        </ActionButton>
      </div>
      <TextBlock className="text-xs text-mist">
        Keluarkan semua perangkat menghentikan semua masuk akun ini. Kosongkan slot perangkat melakukan hal yang sama
        dan dicatat sebagai pengosongan slot, dipakai bila karyawan tidak bisa masuk karena batas perangkat.
      </TextBlock>
    </div>
  );
}
