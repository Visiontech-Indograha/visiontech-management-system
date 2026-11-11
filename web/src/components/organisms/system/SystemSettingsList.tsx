import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { settingErrorMessage, settingSourceLabel } from "@/lib/systemSettings";
import { useSystemSettings, useUpdateSystemSetting, type SystemSetting } from "@/services/systemSettingsService";

/** Daftar sakelar setelan sistem; ubah selalu lewat konfirmasi, sakelar nonaktif bila dikunci server. */
export function SystemSettingsList() {
  const settings = useSystemSettings();
  const update = useUpdateSystemSetting();
  const [target, setTarget] = useState<SystemSetting | null>(null);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    setTarget(null);
    setError(null);
  };
  const confirm = async () => {
    if (!target) return;
    setError(null);
    try {
      await update.mutateAsync({ key: target.key, value: !target.value });
      toast.success(`${target.label} ${target.value ? "dimatikan" : "dinyalakan"}.`);
      close();
    } catch (err) {
      setError(settingErrorMessage(err));
    }
  };

  return (
    <QueryState
      query={settings}
      errorText="Setelan sistem tidak dapat dimuat."
      empty={settings.data?.length === 0}
      emptyText="Belum ada setelan yang bisa diatur."
    >
      <ListBlock className="divide-y divide-line rounded-panel border border-line bg-surface shadow-card">
        {settings.data?.map((s) => (
          <ListEntry key={s.key} className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <TextBlock className="font-medium">{s.label}</TextBlock>
              <TextBlock className="text-sm text-mist">{s.description}</TextBlock>
              <TextBlock className="mt-1 text-xs text-mist">
                {settingSourceLabel(s.source)}
                {s.locked && " · dikunci server, tidak bisa diubah di sini"}
              </TextBlock>
            </div>
            <div className="flex items-center gap-3">
              <Pill tone={s.value ? "success" : "neutral"}>{s.value ? "Menyala" : "Mati"}</Pill>
              <ActionButton
                variant="outline"
                role="switch"
                aria-checked={s.value}
                aria-label={`${s.label}: ${s.value ? "matikan" : "nyalakan"}`}
                disabled={s.locked}
                onClick={() => setTarget(s)}
              >
                {s.value ? "Matikan" : "Nyalakan"}
              </ActionButton>
            </div>
          </ListEntry>
        ))}
      </ListBlock>
      <ConfirmDialog
        open={target !== null}
        title={target ? `${target.value ? "Matikan" : "Nyalakan"} ${target.label}?` : ""}
        message={target ? `${target.description} Perubahan ini berlaku untuk semua pengguna.` : ""}
        confirmLabel={target?.value ? "Ya, matikan" : "Ya, nyalakan"}
        busy={update.isPending}
        error={error}
        onConfirm={confirm}
        onClose={close}
      />
    </QueryState>
  );
}
