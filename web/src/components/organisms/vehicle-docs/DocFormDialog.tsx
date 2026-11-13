import type { ReactNode } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DialogCancelButton } from "@/components/molecules/DialogActions";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDirtyForm } from "@/hooks/useDirtyForm";

/** Kerangka dialog form dokumen kendaraan: judul, galat umum, isi, tombol Batal/Simpan. */
export function DocFormDialog({ title, submitLabel, submitting, formError, onClose, onSubmit, children }: {
  title: string;
  submitLabel: string;
  submitting: boolean;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  const dirtyForm = useDirtyForm();
  return (
    <VmsDialog
      dirty={dirtyForm.dirty}
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <DialogCancelButton onCancel={onClose} disabled={submitting} />
          <ActionButton type="submit" form="doc-form" disabled={submitting}>{submitting ? "Menyimpan..." : submitLabel}</ActionButton>
        </>
      }
    >
      <FormBlock {...dirtyForm.formProps} id="doc-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        {children}
      </FormBlock>
    </VmsDialog>
  );
}
