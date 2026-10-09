import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { employeeName, useActiveEmployees, type WorkPlan } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";

type Overtime = components["schemas"]["OvertimeResponse"];
const key = (planId: string) => ["overtime", planId] as const;

const useOvertime = (planId: string) =>
  useQuery({
    queryKey: key(planId),
    queryFn: async () => (await api.get<Overtime[]>("/overtime", { params: { work_plan_id: planId } })).data,
  });

function useOvertimeMutation<V>(planId: string, fn: (v: V) => Promise<Overtime>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: key(planId) });
      await qc.invalidateQueries({ queryKey: ["overtime-recap"] });
    },
  });
}

function FormDialog({
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

const reportSchema = z.object({
  hours: z
    .string()
    .trim()
    .min(1, "Jam lembur wajib diisi.")
    .refine((v) => Number(v) > 0 && Number(v) <= 12, { message: "Jam lembur harus lebih dari 0 dan paling banyak 12." }),
  reason: z.string().trim().min(1, "Alasan lembur wajib diisi."),
});
type ReportValues = z.infer<typeof reportSchema>;

/** "Ajukan Lembur" — ketua/anggota SK berjalan (POST /overtime). Tanggal lembur dicatat server. */
export function OvertimeDialog({ plan, onClose }: { plan: WorkPlan; onClose: () => void }) {
  const report = useOvertimeMutation(plan.id, async (body: components["schemas"]["OvertimeCreate"]) =>
    (await api.post<Overtime>("/overtime", body)).data,
  );
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
    <FormDialog title="Ajukan Lembur" submitLabel="Ajukan lembur" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Jumlah jam" inputMode="decimal" hint="Maksimal 12 jam." error={errors.hours?.message} {...register("hours")} />
      <TextAreaField label="Alasan" error={errors.reason?.message} {...register("reason")} />
    </FormDialog>
  );
}

/** Panel "Rekap Lembur" per SK (GET /overtime?work_plan_id); PM (create:plan) meninjau yang PENDING_PM. */
export function OvertimePanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canReview = !!me?.permissions.includes("create:plan");
  const list = useOvertime(plan.id);
  const employees = useActiveEmployees();
  const [reviewing, setReviewing] = useState<Overtime | null>(null);
  if (list.data?.length === 0) return null;
  return (
    <section aria-label="Rekap Lembur" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Rekap Lembur</TextBlock>
      <QueryState query={list} errorText="Data lembur tidak dapat dimuat.">
        <ListBlock className="space-y-3">
          {list.data?.map((o) => (
            <ListEntry key={o.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
              <div className="flex items-start justify-between gap-2">
                <TextBlock as="strong" className="text-sm">{employeeName(employees.data, o.employee_id)}</TextBlock>
                <StatusBadge status={o.status} />
              </div>
              <TextBlock className="text-sm">
                {o.hours} jam · {o.reason}
              </TextBlock>
              <TextBlock className="text-xs text-mist">
                {formatDate(o.work_date)}
                {o.review_note ? ` · ${o.review_note}` : ""}
              </TextBlock>
              {canReview && o.status === "PENDING_PM" && (
                <ActionButton size="sm" className="mt-2" onClick={() => setReviewing(o)}>
                  Tinjau lembur
                </ActionButton>
              )}
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
      {reviewing && <ReviewDialog plan={plan} item={reviewing} onClose={() => setReviewing(null)} />}
    </section>
  );
}

const reviewSchema = z.object({ decision: z.enum(["APPROVED", "REJECTED"]), note: z.string().trim() });
type ReviewValues = z.infer<typeof reviewSchema>;

function ReviewDialog({ plan, item, onClose }: { plan: WorkPlan; item: Overtime; onClose: () => void }) {
  const review = useOvertimeMutation(plan.id, async (body: components["schemas"]["OvertimeReview"]) =>
    (await api.post<Overtime>(`/overtime/${item.id}/review`, body)).data,
  );
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
    <FormDialog title="Tinjau lembur" submitLabel="Simpan keputusan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextBlock className="mb-3 text-sm">
        {item.hours} jam · {item.reason}
      </TextBlock>
      <SelectField label="Keputusan" {...register("decision")}>
        <ControlOption value="APPROVED">Setujui</ControlOption>
        <ControlOption value="REJECTED">Tolak</ControlOption>
      </SelectField>
      <TextAreaField label="Catatan (opsional)" {...register("note")} />
    </FormDialog>
  );
}
