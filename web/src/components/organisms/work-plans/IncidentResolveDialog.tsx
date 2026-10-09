import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import type { WorkPlan } from "@/services/workPlanService";
import { type Incident, resolveIncident, useStoreIncident } from "@/services/incidentService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

const resolveSchema = z.object({ resolution_note: z.string().trim().min(1, "Catatan penyelesaian wajib diisi.") });

export function IncidentResolveDialog({ plan, incident, onClose }: { plan: WorkPlan; incident: Incident; onClose: () => void }) {
  const store = useStoreIncident(plan.id);
  const resolve = useMutation({
    mutationFn: (body: { resolution_note: string }) => resolveIncident(incident.id, body),
    onSuccess: store,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ resolution_note: string }>({ resolver: zodResolver(resolveSchema), defaultValues: { resolution_note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await resolve.mutateAsync(v);
      toast.success("Insiden diselesaikan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <VmsDialog
      open
      title="Selesaikan insiden"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="resolve-form" disabled={isSubmitting}>
            Selesaikan
          </ActionButton>
        </>
      }
    >
      <FormBlock id="resolve-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <TextAreaField label="Catatan penyelesaian" error={errors.resolution_note?.message} {...register("resolution_note")} />
      </FormBlock>
    </VmsDialog>
  );
}
