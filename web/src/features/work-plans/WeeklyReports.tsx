import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField } from "@/components/ui/Field";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "./api";

type Week = components["schemas"]["WeeklyReportResponse"];
type WeeklyReportRequest = components["schemas"]["WeeklyReportRequest"];
type WeeklyReviewRequest = components["schemas"]["WeeklyReviewRequest"];

const EDITABLE = ["DRAFT", "CHANGES_REQUESTED"];

function useWeeks(planId: string) {
  return useQuery({
    queryKey: ["weekly", planId],
    queryFn: async () => (await api.get<Week[]>(`/work-plans/${planId}/weekly`)).data,
  });
}

function useWeekMutation<V>(planId: string, fn: (v: V) => Promise<Week>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["weekly", planId] }) });
}

/** Laporan mingguan SK (GET/PUT/submit/review /work-plans/{id}/weekly), mengikuti prototype renderWeek. */
export function WeeklyReports({ plan }: { plan: WorkPlan }) {
  const weeks = useWeeks(plan.id);
  return (
    <section aria-label="Laporan mingguan" className="space-y-3">
      <h2 className="text-base font-semibold">Laporan mingguan</h2>
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
          <h3 className="font-medium">{week.name}</h3>
          <p className="text-sm text-mist">
            {formatDate(week.starts_on)} – {formatDate(week.ends_on)}
          </p>
        </div>
        <StatusBadge status={week.status} />
      </header>
      {children}
    </article>
  );
}

function WeekPanel({ plan, week }: { plan: WorkPlan; week: Week }) {
  const { me } = useSession();
  const isPM = !!me?.permissions.includes("create:plan");
  const active = plan.status === "IN_PROGRESS";

  if (EDITABLE.includes(week.status) && active) {
    return (
      <Panel week={week}>
        {!week.days_approved ? (
          <p className="text-sm text-mist">
            Semua laporan harian dalam minggu ini harus disetujui PM sebelum laporan mingguan dapat dibuat.
          </p>
        ) : (
          <WeeklyForm plan={plan} week={week} />
        )}
      </Panel>
    );
  }
  return (
    <Panel week={week}>
      {week.body ? (
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-mist">Laporan</dt>
            <dd className="whitespace-pre-line">{week.body}</dd>
          </div>
          <div>
            <dt className="text-mist">Kendala</dt>
            <dd className="whitespace-pre-line">{week.obstacle}</dd>
          </div>
          {week.review_note && (
            <div>
              <dt className="text-mist">Catatan PM</dt>
              <dd>{week.review_note}</dd>
            </div>
          )}
        </dl>
      ) : (
        <p className="text-sm text-mist">Belum ada laporan mingguan.</p>
      )}
      {week.status === "SUBMITTED" && isPM && <WeeklyReviewForm plan={plan} week={week} />}
    </Panel>
  );
}

const weeklySchema = z.object({
  body: z.string().trim().min(1, "Laporan mingguan wajib diisi."),
  obstacle: z.string().trim().min(1, 'Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).'),
});

/** Ketua menulis laporan (PUT) lalu mengirim (POST submit). API menolak bila bukan ketua. */
function WeeklyForm({ plan, week }: { plan: WorkPlan; week: Week }) {
  const save = useWeekMutation(plan.id, async (body: WeeklyReportRequest) => (await api.put<Week>(`/work-plans/${plan.id}/weekly/${week.week}`, body)).data);
  const submit = useWeekMutation<void>(plan.id, async () => (await api.post<Week>(`/work-plans/${plan.id}/weekly/${week.week}/submit`)).data);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<WeeklyReportRequest>({ resolver: zodResolver(weeklySchema), defaultValues: { body: week.body, obstacle: week.obstacle } });

  const send = (andSubmit: boolean) =>
    handleSubmit(async (v) => {
      setFormError(null);
      try {
        await save.mutateAsync(v);
        if (andSubmit) await submit.mutateAsync();
        toast.success(andSubmit ? "Laporan mingguan dikirim." : "Draft laporan mingguan disimpan.");
      } catch (err) {
        setFormError(errorMessage(err));
      }
    });

  return (
    <form noValidate onSubmit={send(true)}>
      {formError && (
        <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      {week.review_note && <p className="mb-3 text-sm text-warning">Catatan PM: {week.review_note}</p>}
      <TextAreaField label="Laporan Mingguan" error={errors.body?.message} {...register("body")} />
      <TextAreaField label="Ringkasan Kendala Mingguan (Wajib)" error={errors.obstacle?.message} {...register("obstacle")} />
      <div className="flex flex-col gap-2 md:flex-row md:justify-end">
        <Button type="button" variant="outline" onClick={send(false)} disabled={isSubmitting}>
          Simpan draft
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          Kirim laporan
        </Button>
      </div>
    </form>
  );
}

const reviewSchema = z
  .object({ decision: z.enum(["APPROVE", "RETURN"]), note: z.string().trim() })
  .refine((v) => v.decision === "APPROVE" || v.note.length > 0, { path: ["note"], message: "Catatan revisi wajib diisi." });
type ReviewValues = z.infer<typeof reviewSchema>;

function WeeklyReviewForm({ plan, week }: { plan: WorkPlan; week: Week }) {
  const review = useWeekMutation(plan.id, async (body: WeeklyReviewRequest) => (await api.post<Week>(`/work-plans/${plan.id}/weekly/${week.week}/review`, body)).data);
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
    <form noValidate onSubmit={onSubmit} className="mt-4 border-t border-line pt-4">
      {formError && (
        <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      <SelectField label="Keputusan" {...register("decision")}>
        <option value="APPROVE">Setujui laporan</option>
        <option value="RETURN">Minta perbaikan</option>
      </SelectField>
      <TextAreaField label="Catatan (wajib jika dikembalikan)" error={errors.note?.message} {...register("note")} />
      <div className="flex justify-end">
        <Button type="submit" disabled={isSubmitting}>
          Simpan keputusan
        </Button>
      </div>
    </form>
  );
}
