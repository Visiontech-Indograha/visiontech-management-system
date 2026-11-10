import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
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
  error,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  danger?: boolean;
  /** Galat dari aksi sebelumnya; ditampilkan di dalam dialog. */
  error?: string | null;
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
      <FormErrorText message={error} />
      <TextBlock className="text-sm text-mist">{message}</TextBlock>
    </VmsDialog>
  );
}
