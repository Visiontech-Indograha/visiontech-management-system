import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useTransition, type Transition, type WorkPlan } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock } from "@/components/molecules/FormBlock";

function FormDialog({
  title,
  formId,
  submitting,
  submitLabel = "Simpan",
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  formId: string;
  submitting: boolean;
  submitLabel?: string;
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
          <ActionButton type="submit" form={formId} disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </ActionButton>
        </>
      }
    >
      <FormBlock id={formId} onSubmit={onSubmit} noValidate className="max-h-[65vh] overflow-y-auto px-1">
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

const required = (msg: string) => z.string().trim().min(1, msg);

const reasonSchema = z.object({ reason: required("Alasan wajib diisi.") });

/** Dialog alasan untuk banding, batal, arsip (TransitionRequest.reason). */
export function PlanReasonDialog({
  plan,
  action,
  title,
  label,
  onClose,
}: {
  plan: WorkPlan;
  action: Transition;
  title: string;
  label: string;
  onClose: () => void;
}) {
  const transition = useTransition(plan.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ reason: string }>({ resolver: zodResolver(reasonSchema), defaultValues: { reason: "" } });
  const onSubmit = handleSubmit(async ({ reason }) => {
    setFormError(null);
    try {
      await transition.mutateAsync({ action, row_version: plan.row_version, reason });
      toast.success(`${title} berhasil.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={title} formId="reason" submitting={isSubmitting} submitLabel={title} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextAreaField label={label} error={errors.reason?.message} {...register("reason")} />
    </FormDialog>
  );
}
