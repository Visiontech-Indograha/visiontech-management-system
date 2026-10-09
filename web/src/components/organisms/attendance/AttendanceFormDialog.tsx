import type { ReactNode } from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock } from "@/components/molecules/FormBlock";

/** Kerangka dialog form absensi: judul, galat umum, isi form, tombol Batal/kirim. */
export function AttendanceFormDialog({
  title,
  submitLabel,
  submitting,
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submitLabel: string;
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
          <ActionButton variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="attendance-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="attendance-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        {children}
      </FormBlock>
    </VmsDialog>
  );
}
