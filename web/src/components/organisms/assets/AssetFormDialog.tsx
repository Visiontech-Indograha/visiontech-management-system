import type { ReactNode } from "react";
import { Button } from "@/components/atoms/Button";
import { VmsDialog } from "@/components/molecules/VmsDialog";

/** Kerangka dialog form aset: judul, galat umum, isi form, tombol Batal/Simpan. */
export function AssetFormDialog({
  title,
  submitLabel = "Simpan",
  submitting,
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submitLabel?: string;
  submitting: boolean;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  return (
    <VmsDialog
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </Button>
          <Button type="submit" form="asset-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </Button>
        </>
      }
    >
      <form id="asset-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {children}
      </form>
    </VmsDialog>
  );
}
