import { Button } from "../atoms/Button";
import { useDialogGuard } from "@/lib/dialogGuard";

/**
 * Tombol Batal untuk footer dialog. Di dalam VmsDialog, klik Batal ikut dijaga:
 * formulir yang sudah berubah meminta konfirmasi lebih dulu.
 */
export function DialogCancelButton({ onCancel, disabled, children = "Batal" }: {
  onCancel: () => void;
  disabled?: boolean;
  children?: React.ReactNode;
}) {
  const guard = useDialogGuard();
  return (
    <Button variant="outline" onClick={() => guard(onCancel)} disabled={disabled}>
      {children}
    </Button>
  );
}

/**
 * Tombol kaki dialog formulir: "Batal" + tombol kirim untuk `<form id={formId}>`.
 *
 *   <DialogActions onCancel={onClose} busy={isSubmitting} formId="site-form" />
 */
export function DialogActions({ onCancel, busy, submitDisabled, formId, submitLabel = "Simpan", busyLabel = "Menyimpan...", cancelLabel = "Batal" }: {
  onCancel: () => void;
  busy: boolean;
  /** Simpan nonaktif tanpa mengubah teks dan tanpa mengunci Batal (mis. pilihan diblokir). */
  submitDisabled?: boolean;
  formId: string;
  submitLabel?: string;
  busyLabel?: string;
  cancelLabel?: string;
}) {
  return (
    <>
      <DialogCancelButton onCancel={onCancel} disabled={busy}>
        {cancelLabel}
      </DialogCancelButton>
      <Button type="submit" form={formId} disabled={busy || submitDisabled}>
        {busy ? busyLabel : submitLabel}
      </Button>
    </>
  );
}
