import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { type WorkPlan } from "@/services/workPlanService";
import { createOvertime, useOvertimeMutation } from "@/services/overtimeService";
import { OvertimeFormDialog } from "@/components/organisms/work-plans/OvertimeFormDialog";

const reportSchema = z.object({
  hours: z
    .string()
    .trim()
    .min(1, "Jam lembur wajib diisi.")
    .refine((v) => Number(v) > 0 && Number(v) <= 12, { message: "Jam lembur harus lebih dari 0 dan paling banyak 12." }),
  reason: z.string().trim().min(1, "Alasan lembur wajib diisi."),
});

type ReportValues = z.infer<typeof reportSchema>;

/** "Ajukan Lembur" — ketua/anggota rencana kerja berjalan (POST /overtime). Tanggal lembur dicatat server. */
export function OvertimeDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const report = useOvertimeMutation(plan.id, (body: components["schemas"]["OvertimeCreate"]) => createOvertime(body));
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReportValues>({ resolver: zodResolver(reportSchema), defaultValues: { hours: "", reason: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await report.mutateAsync({ work_plan_id: plan.id, hours: Number(v.hours), reason: v.reason });
      toast.success("Lembur diajukan ke PM.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <OvertimeFormDialog title="Ajukan Lembur" submitLabel="Ajukan lembur" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Jumlah jam" inputMode="decimal" hint="Maksimal 12 jam." error={errors.hours?.message} {...register("hours")} />
      <TextAreaField label="Alasan" error={errors.reason?.message} {...register("reason")} />
    </OvertimeFormDialog>
  );
}
