import { Button } from "../atoms/Button";

/**
 * Tombol kaki dialog formulir: "Batal" + tombol kirim untuk `<form id={formId}>`.
 *
 *   <DialogActions onCancel={onClose} busy={isSubmitting} formId="site-form" />
 */
export function DialogActions({ onCancel, busy, formId, submitLabel = "Simpan", busyLabel = "Menyimpan...", cancelLabel = "Batal" }: {
  onCancel: () => void;
  busy: boolean;
  formId: string;
  submitLabel?: string;
  busyLabel?: string;
  cancelLabel?: string;
}) {
  return (
    <>
      <Button variant="outline" onClick={onCancel} disabled={busy}>
        {cancelLabel}
      </Button>
      <Button type="submit" form={formId} disabled={busy}>
        {busy ? busyLabel : submitLabel}
      </Button>
    </>
  );
}
