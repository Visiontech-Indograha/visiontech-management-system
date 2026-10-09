import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useFormDraft } from "@/hooks/useFormDraft";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { SelectField, TextAreaField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock } from "@/components/molecules/ListBlock";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { listWeeklyReports, reviewWeeklyReport, saveWeeklyReport, submitWeeklyReport, type WeeklyReport, type WeeklyReportRequest, type WeeklyReviewRequest } from "@/services/weeklyReportService";

type Week = WeeklyReport;

const EDITABLE = ["DRAFT", "CHANGES_REQUESTED"];

function useWeeks(planId: string) {
  return useQuery({
    queryKey: ["weekly", planId],
    queryFn: () => listWeeklyReports(planId),
  });
}

function useWeekMutation<V>(planId: string, fn: (v: V) => Promise<Week>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["weekly", planId] }) });
}

/** Laporan mingguan SK (GET/PUT/submit/review /work-plans/{id}/weekly), mengikuti prototype renderWeek. */
export function WeeklyReportsPanel({ plan }: { plan: WorkPlan }) {
  const weeks = useWeeks(plan.id);
  return (
    <section aria-label="Laporan mingguan" className="space-y-3">
      <TextBlock as="h2" className="text-base font-semibold">Laporan mingguan</TextBlock>
      <QueryState query={weeks} errorText="Laporan mingguan tidak dapat dimuat." empty={weeks.data?.length === 0} emptyText="Belum ada laporan mingguan.">
        {weeks.data?.map((w) => <WeekPanel key={w.week} plan={plan} week={w} />)}
      </QueryState>
    </section>
  );
}

function Panel({ week, children }: { week: Week; children: ReactNode }) {
  return (
    <article aria-label={week.name} className="rounded-panel border border-line bg-surface shadow-card p-4">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <TextBlock as="h3" className="font-medium">{week.name}</TextBlock>
          <TextBlock className="text-sm text-mist">
            {formatDate(week.starts_on)} – {formatDate(week.ends_on)}
          </TextBlock>
        </div>
        <StatusBadge status={week.status === "SUBMITTED" && week.resubmitted ? "RESUBMITTED" : week.status} />
      </header>
      {children}
    </article>
  );
}

function WeekPanel({ plan, week }: { plan: WorkPlan; week: Week }) {
  const { me } = useSession();
  const isPM = !!me?.permissions.includes("create:plan");
  const isLeader = !!me?.employee_id && me.employee_id === plan.leader_employee_id;
  const active = plan.status === "IN_PROGRESS";
  const [viewing, setViewing] = useState(false);

  // Alur SK v2: laporan mingguan diisi ketua di HP; PM hanya memeriksa.
  if (EDITABLE.includes(week.status) && active && isLeader) {
    return (
      <Panel week={week}>
        {!week.days_approved ? (
          <TextBlock className="text-sm text-mist">
            Semua laporan harian dalam minggu ini harus disetujui PM sebelum laporan mingguan dapat dibuat.
          </TextBlock>
        ) : (
          <WeeklyForm plan={plan} week={week} />
        )}
      </Panel>
    );
  }
  return (
    <Panel week={week}>
      {week.body ? (
        <ListBlock as="dl" className="space-y-2 text-sm">
          <div>
            <TextBlock as="dt" className="text-mist">Laporan</TextBlock>
            <TextBlock as="dd" className="whitespace-pre-line">{week.body}</TextBlock>
          </div>
          <div>
            <TextBlock as="dt" className="text-mist">Kendala</TextBlock>
            <TextBlock as="dd" className="whitespace-pre-line">{week.obstacle}</TextBlock>
          </div>
          {week.review_note && (
            <div>
              <TextBlock as="dt" className="text-mist">Catatan PM</TextBlock>
              <TextBlock as="dd">{week.review_note}</TextBlock>
            </div>
          )}
        </ListBlock>
      ) : (
        <TextBlock className="text-sm text-mist">Belum ada laporan mingguan.</TextBlock>
      )}
      {week.status === "SUBMITTED" && isPM && <WeeklyReviewForm plan={plan} week={week} />}
      {week.status === "APPROVED" && (
        <ActionButton variant="outline" size="sm" className="mt-3" onClick={() => setViewing(true)}>
          Lihat laporan
        </ActionButton>
      )}
      {viewing && (
        <PlanPreviewDialog title={week.name} path={`/work-plans/${plan.id}/weekly/${week.week}/report/html`} onClose={() => setViewing(false)} />
      )}
    </Panel>
  );
}

const weeklySchema = z.object({
  body: z.string().trim().min(1, "Laporan mingguan wajib diisi."),
  obstacle: z.string().trim().min(1, 'Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).'),
});

/** Ketua menulis laporan (PUT) lalu mengirim (POST submit). API menolak bila bukan ketua. */
function WeeklyForm({ plan, week }: { plan: WorkPlan; week: Week }) {
  const save = useWeekMutation(plan.id, (body: WeeklyReportRequest) => saveWeeklyReport(plan.id, week.week, body));
  const submit = useWeekMutation<void>(plan.id, () => submitWeeklyReport(plan.id, week.week));
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<WeeklyReportRequest>({ resolver: zodResolver(weeklySchema), defaultValues: { body: week.body, obstacle: week.obstacle } });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;
  const dropDraft = useFormDraft(`weekly:${plan.id}:${week.week}`, form);

  const send = (andSubmit: boolean) =>
    handleSubmit(async (v) => {
      setFormError(null);
      try {
        await save.mutateAsync(v);
        dropDraft();
        if (andSubmit) await submit.mutateAsync();
        toast.success(andSubmit ? "Laporan mingguan dikirim." : "Draft laporan mingguan disimpan.");
      } catch (err) {
        setFormError(errorMessage(err));
      }
    });

  return (
    <FormBlock noValidate onSubmit={send(true)}>
      {formError && (
        <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {formError}
        </TextBlock>
      )}
      {week.review_note && <TextBlock className="mb-3 text-sm text-warning">Catatan PM: {week.review_note}</TextBlock>}
      <TextAreaField label="Laporan Mingguan" error={errors.body?.message} {...register("body")} />
      <TextAreaField label="Ringkasan Kendala Mingguan (Wajib)" error={errors.obstacle?.message} {...register("obstacle")} />
      <div className="flex flex-col gap-2 md:flex-row md:justify-end">
        <ActionButton type="button" variant="outline" onClick={send(false)} disabled={isSubmitting}>
          Simpan draft
        </ActionButton>
        <ActionButton type="submit" disabled={isSubmitting}>
          Kirim laporan
        </ActionButton>
      </div>
    </FormBlock>
  );
}

const reviewSchema = z
  .object({ decision: z.enum(["APPROVE", "RETURN"]), note: z.string().trim() })
  .refine((v) => v.decision === "APPROVE" || v.note.length > 0, { path: ["note"], message: "Catatan revisi wajib diisi." });
type ReviewValues = z.infer<typeof reviewSchema>;

function WeeklyReviewForm({ plan, week }: { plan: WorkPlan; week: Week }) {
  const review = useWeekMutation(plan.id, (body: WeeklyReviewRequest) => reviewWeeklyReport(plan.id, week.week, body));
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReviewValues>({ resolver: zodResolver(reviewSchema), defaultValues: { decision: "APPROVE", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await review.mutateAsync({ decision: v.decision, note: v.note || null });
      toast.success("Keputusan disimpan.");
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormBlock noValidate onSubmit={onSubmit} className="mt-4 border-t border-line pt-4">
      {formError && (
        <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {formError}
        </TextBlock>
      )}
      <SelectField label="Keputusan" {...register("decision")}>
        <ControlOption value="APPROVE">Setujui laporan</ControlOption>
        <ControlOption value="RETURN">Minta perbaikan</ControlOption>
      </SelectField>
      <TextAreaField label="Catatan (wajib jika dikembalikan)" error={errors.note?.message} {...register("note")} />
      <div className="flex justify-end">
        <ActionButton type="submit" disabled={isSubmitting}>
          Simpan keputusan
        </ActionButton>
      </div>
    </FormBlock>
  );
}
