import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";

/** Konfirmasi singkat sebelum aksi penting/tak terbalik; tombol dinonaktifkan selama diproses (anti klik ganda). */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Ya, lanjutkan",
  busy = false,
  danger = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <VmsDialog
      open={open}
      title={title}
      onClose={() => !busy && onClose()}
      footer={
        <div className="flex w-full items-center justify-end gap-2">
          <ActionButton variant="outline" onClick={onClose} disabled={busy}>
            Batal
          </ActionButton>
          <ActionButton variant={danger ? "destructive" : "default"} onClick={onConfirm} disabled={busy}>
            {busy ? "Memproses…" : confirmLabel}
          </ActionButton>
        </div>
      }
    >
      <TextBlock className="text-sm text-mist">{message}</TextBlock>
    </VmsDialog>
  );
}
