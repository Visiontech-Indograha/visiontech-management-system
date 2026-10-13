import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

export function OvertimeFormDialog({
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
  children: React.ReactNode;
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
          <ActionButton type="submit" form="overtime-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="overtime-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        {children}
      </FormBlock>
    </VmsDialog>
  );
}
