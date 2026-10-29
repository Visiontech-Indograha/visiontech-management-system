import type { ReactNode } from "react";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { DialogCancelButton } from "@/components/molecules/DialogActions";
import { useDirtyForm } from "@/hooks/useDirtyForm";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

/** Kerangka dialog form aset: judul, galat umum, isi form, tombol Batal/Simpan. */
export function AssetFormDialog({
  title,
  submitLabel = "Simpan",
  submitting,
  submitDisabled = false,
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submitLabel?: string;
  submitting: boolean;
  /** Tombol simpan nonaktif (mis. bentrok jadwal) selain saat sedang menyimpan. */
  submitDisabled?: boolean;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  const dirtyForm = useDirtyForm();
  return (
    <VmsDialog dirty={dirtyForm.dirty}
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <DialogCancelButton onCancel={onClose} disabled={submitting} />
          <ActionButton type="submit" form="asset-form" disabled={submitting || submitDisabled}>
            {submitting ? "Menyimpan..." : submitLabel}
          </ActionButton>
        </>
      }
    >
      <FormBlock {...dirtyForm.formProps} id="asset-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        {children}
      </FormBlock>
    </VmsDialog>
  );
}
