import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { type WorkPlan } from "@/services/workPlanService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ControlOption } from "@/components/molecules/FormBlock";
import { reviewOvertime, type Overtime, useOvertimeMutation } from "@/services/overtimeService";
import { OvertimeFormDialog } from "@/components/organisms/work-plans/OvertimeFormDialog";

const reviewSchema = z.object({ decision: z.enum(["APPROVED", "REJECTED"]), note: z.string().trim() });

type ReviewValues = z.infer<typeof reviewSchema>;

export function OvertimeReviewDialog({ plan, item, onClose }: { plan: WorkPlan; item: Overtime; onClose: () => void }) {
  const review = useOvertimeMutation(plan.id, (body: components["schemas"]["OvertimeReview"]) => reviewOvertime(item.id, body));
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<ReviewValues>({ resolver: zodResolver(reviewSchema), defaultValues: { decision: "APPROVED", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await review.mutateAsync({ decision: v.decision, note: v.note || null });
      toast.success(v.decision === "APPROVED" ? "Lembur disetujui." : "Lembur ditolak.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <OvertimeFormDialog title="Tinjau lembur" submitLabel="Simpan keputusan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextBlock className="mb-3 text-sm">
        {item.hours} jam · {item.reason}
      </TextBlock>
      <SelectField label="Keputusan" {...register("decision")}>
        <ControlOption value="APPROVED">Setujui</ControlOption>
        <ControlOption value="REJECTED">Tolak</ControlOption>
      </SelectField>
      <TextAreaField label="Catatan (opsional)" {...register("note")} />
    </OvertimeFormDialog>
  );
}
