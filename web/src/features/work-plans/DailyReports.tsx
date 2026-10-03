import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFormDraft } from "@/lib/drafts";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { FilePreview } from "@/components/molecules/FilePreview";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField, TextField } from "@/components/ui/Field";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { formatDate, formatDateTime } from "@/lib/format";
import type { WorkPlan } from "./api";
import { SkPreviewDialog } from "./SkPreviewDialog";
import { oversize, uploadFiles } from "./uploads";

type S = components["schemas"];
type Day = S["PlanDayOut"];
type Task = S["DayTaskOut"];
type ReportIn = S["DailyReportCreate"];
type ReviewIn = S["ReportReviewRequest"];
type MemberReport = S["MemberReportOut"];

const LOCKED = ["SUBMITTED", "APPROVED"];
const daysKey = (planId: string) => ["plan-days", planId] as const;

/** Tanggal hari ini (zona lokal) dalam bentuk YYYY-MM-DD, pembanding work_date. */
function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function useDayMutation<V>(planId: string, fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: daysKey(planId) }),
  });
}

/**
 * Laporan harian SK (GET /work-plans/{id}/days) — checklist tugas (toggle), isi & kirim laporan (ketua),
 * review PM. Tindakan ketua ditampilkan kepada semua; API menolak dengan pesan jelas bila bukan ketua.
 */
export function DailyReports({ plan }: { plan: WorkPlan }) {
  const days = useQuery({
    queryKey: daysKey(plan.id),
    queryFn: async () => (await api.get<Day[]>(`/work-plans/${plan.id}/days`)).data,
  });
  return (
    <section aria-label="Laporan harian" className="space-y-3">
      <h2 className="text-base font-semibold">Laporan harian</h2>
      <QueryState
        query={days}
        errorText="Laporan harian tidak dapat dimuat."
        empty={days.data?.length === 0}
        emptyText="Belum ada hari kerja."
      >
        {days.data?.map((d) => (
          <DayPanel key={d.id} plan={plan} day={d} />
        ))}
      </QueryState>
    </section>
  );
}

/** Rincian harian SK sebelum berjalan (draf s.d. diterima): tanggal, judul, tugas — hanya baca. */
export function DayPlanList({ plan }: { plan: WorkPlan }) {
  const days = useQuery({
    queryKey: daysKey(plan.id),
    queryFn: async () => (await api.get<Day[]>(`/work-plans/${plan.id}/days`)).data,
  });
  return (
    <section aria-label="Rincian harian" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <h2 className="mb-3 text-base font-semibold">Rincian harian</h2>
      <QueryState
        query={days}
        errorText="Rincian harian tidak dapat dimuat."
        empty={days.data?.length === 0}
        emptyText="Belum ada hari kerja. Setiap tanggal dalam periode wajib diisi sebelum SK diterbitkan."
      >
        <ol className="space-y-3">
          {days.data?.map((d) => (
            <li key={d.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
              <p className="font-medium">
                {formatDate(d.work_date)} · {d.title}
              </p>
              <ul className="mt-1 list-disc pl-5 text-sm text-mist">
                {d.tasks.map((t) => (
                  <li key={t.id}>{t.title}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </QueryState>
    </section>
  );
}

function DayPanel({ plan, day }: { plan: WorkPlan; day: Day }) {
  const { me } = useSession();
  const isPM = !!me?.permissions.includes("create:plan");
  // Alur SK v2: hanya ketua menurut SK yang mengisi laporan (di HP); PM tidak melihat form ketua (CELAH 7).
  const isLeader = !!me?.employee_id && me.employee_id === plan.leader_employee_id;
  const status = day.report?.status ?? "DRAFT";
  const badge = status === "SUBMITTED" && day.report?.resubmitted ? "RESUBMITTED" : status;
  const reached = day.work_date <= today();
  const editable = isLeader && plan.status === "IN_PROGRESS" && reached && !LOCKED.includes(status);
  const [viewing, setViewing] = useState(false);
  const label = `${day.title || "Hari kerja"} — ${formatDate(day.work_date)}`;

  return (
    <article aria-label={label} className="rounded-panel border border-line bg-surface shadow-card p-4">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-medium">{day.title || "Hari kerja"}</h3>
          <p className="text-sm text-mist">{formatDate(day.work_date)}</p>
        </div>
        <div className="flex items-center gap-2">
          {day.report ? <StatusBadge status={badge} /> : <span className="text-sm text-mist">Belum ada laporan</span>}
          {status === "APPROVED" && (
            <Button variant="outline" size="sm" onClick={() => setViewing(true)}>
              Lihat laporan
            </Button>
          )}
        </div>
      </header>
      <TaskList plan={plan} day={day} editable={editable} />
      {!reached ? (
        <p className="mt-3 text-sm text-mist">Laporan dapat diisi mulai {formatDate(day.work_date)}.</p>
      ) : editable ? (
        <DailyForm plan={plan} day={day} />
      ) : (
        <ReportView day={day} />
      )}
      {(day.member_reports_sent ?? 0) > 0 && <MemberReports plan={plan} day={day} />}
      {status === "SUBMITTED" && isPM && ["IN_PROGRESS", "COMPLETION_REVIEW"].includes(plan.status) && (
        <DailyReviewForm plan={plan} day={day} />
      )}
      {viewing && (
        <SkPreviewDialog
          title={`Laporan harian — ${formatDate(day.work_date)}`}
          path={`/work-plans/${plan.id}/days/${day.id}/report/html`}
          onClose={() => setViewing(false)}
        />
      )}
    </article>
  );
}

function TaskList({ plan, day, editable }: { plan: WorkPlan; day: Day; editable: boolean }) {
  const toggle = useDayMutation(
    plan.id,
    async (t: Task) => (await api.post(`/work-plans/${plan.id}/days/${day.id}/tasks/${t.id}/toggle`)).data,
  );
  const [error, setError] = useState<string | null>(null);
  if (day.tasks.length === 0) return <p className="text-sm text-mist">Belum ada tugas.</p>;
  const onToggle = async (t: Task) => {
    setError(null);
    try {
      await toggle.mutateAsync(t);
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  return (
    <>
      {error && (
        <p role="alert" className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      <ul aria-label="Tugas" className="space-y-2">
        {[...day.tasks]
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((t) => (
            <li key={t.id}>
              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="size-5"
                  checked={t.is_done}
                  disabled={!editable || toggle.isPending}
                  onChange={() => onToggle(t)}
                />
                <span className={t.is_done ? "text-mist line-through" : undefined}>{t.title}</span>
                {t.done_at && <span className="text-xs text-mist">{formatDateTime(t.done_at)}</span>}
              </label>
            </li>
          ))}
      </ul>
    </>
  );
}

/** Laporan anggota yang dikirim ke ketua (alur SK v2) — dibaca PM saat memeriksa laporan ketua. */
function MemberReports({ plan, day }: { plan: WorkPlan; day: Day }) {
  const reports = useQuery({
    queryKey: ["member-reports", day.id],
    queryFn: async () => (await api.get<MemberReport[]>(`/work-plans/${plan.id}/days/${day.id}/member-reports`)).data,
  });
  const sent = (reports.data ?? []).filter((r) => r.status === "SENT");
  return (
    <details className="mt-3 rounded-control border border-line p-3 text-sm">
      <summary className="cursor-pointer font-medium">Laporan anggota ({day.member_reports_sent})</summary>
      <ul className="mt-2 space-y-2">
        {sent.map((r) => (
          <li key={r.id}>
            <p className="font-medium">
              {r.full_name} <span className="font-normal text-mist">— {r.position}</span>
            </p>
            <p className="whitespace-pre-line">{r.body}</p>
            {r.obstacle && <p className="text-mist">Kendala: {r.obstacle}</p>}
          </li>
        ))}
      </ul>
    </details>
  );
}

function ReportView({ day }: { day: Day }) {
  const r = day.report;
  if (!r || !r.body) return <p className="mt-3 text-sm text-mist">Belum ada laporan harian.</p>;
  return (
    <dl className="mt-3 space-y-2 text-sm">
      <div>
        <dt className="text-mist">Laporan</dt>
        <dd className="whitespace-pre-line">{r.body}</dd>
      </div>
      <div>
        <dt className="text-mist">Kendala</dt>
        <dd className="whitespace-pre-line">{r.obstacle}</dd>
      </div>
      {r.evidence_file_ids.length > 0 && (
        <div>
          <dt className="text-mist">Bukti ({r.evidence_file_ids.length} foto)</dt>
          {/* PM menilai laporan dari foto bukti — tampilkan pratinjau, bukan sekadar jumlah (temuan uji nyata R-17). */}
          <dd className="mt-1 flex flex-wrap gap-2">
            {r.evidence_file_ids.map((id, i) => (
              <FilePreview key={id} fileId={id} fileName={`Bukti ${i + 1}`} />
            ))}
          </dd>
        </div>
      )}
      {r.review_note && (
        <div>
          <dt className="text-mist">Catatan PM</dt>
          <dd>{r.review_note}</dd>
        </div>
      )}
    </dl>
  );
}

const dailySchema = z.object({
  body: z.string().trim().min(10, "Laporan harian minimal 10 karakter."),
  obstacle: z.string().trim().min(1, 'Kendala wajib diisi (isi "Tidak ada" jika lancar).'),
});
type DailyValues = z.infer<typeof dailySchema>;

/** Ketua menyimpan (PUT /days/{day}) lalu mengirim (POST submit); bukti diunggah ke /files/upload dulu. */
function DailyForm({ plan, day }: { plan: WorkPlan; day: Day }) {
  const base = `/work-plans/${plan.id}/days/${day.id}`;
  const save = useDayMutation(plan.id, async (body: ReportIn) => (await api.put(base, body)).data);
  const submit = useDayMutation<void>(plan.id, async () => (await api.post(`${base}/submit`)).data);
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<DailyValues>({
    resolver: zodResolver(dailySchema),
    defaultValues: {
      body: day.report?.body ?? "",
      obstacle: day.report?.obstacle ?? "",
    },
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;
  const dropDraft = useFormDraft(`daily:${day.id}`, form);

  const pickFiles = (list: FileList | null) => {
    const picked = list ? Array.from(list) : [];
    setFileError(oversize(picked));
    setFiles(picked);
  };

  const send = (andSubmit: boolean) =>
    handleSubmit(async (v) => {
      if (fileError) return;
      setFormError(null);
      try {
        const uploaded = await uploadFiles(files);
        await save.mutateAsync({
          ...v,
          evidence_file_ids: [...(day.report?.evidence_file_ids ?? []), ...uploaded],
        });
        dropDraft();
        if (andSubmit) await submit.mutateAsync();
        setFiles([]);
        toast.success(andSubmit ? "Laporan harian dikirim." : "Draft laporan harian disimpan.");
      } catch (err) {
        setFormError(errorMessage(err));
      }
    });

  return (
    <form noValidate onSubmit={send(true)} className="mt-4 border-t border-line pt-4">
      {formError && (
        <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      {day.report?.review_note && <p className="mb-3 text-sm text-warning">Catatan PM: {day.report.review_note}</p>}
      <TextAreaField label="Laporan Harian" error={errors.body?.message} {...register("body")} />
      <TextAreaField label="Kendala (Wajib)" error={errors.obstacle?.message} {...register("obstacle")} />
      <TextField
        label="Bukti Foto/PDF (Opsional)"
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.pdf"
        hint={`Maksimal 10 MB per berkas.${day.report?.evidence_file_ids.length ? ` ${day.report.evidence_file_ids.length} berkas sudah terlampir.` : ""}`}
        error={fileError ?? undefined}
        onChange={(e) => pickFiles(e.target.files)}
      />
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
  .refine((v) => v.decision === "APPROVE" || v.note.length > 0, {
    path: ["note"],
    message: "Catatan revisi wajib diisi.",
  });
type ReviewValues = z.infer<typeof reviewSchema>;

function DailyReviewForm({ plan, day }: { plan: WorkPlan; day: Day }) {
  const review = useDayMutation(
    plan.id,
    async (body: ReviewIn) => (await api.post(`/work-plans/${plan.id}/days/${day.id}/review`, body)).data,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReviewValues>({
    resolver: zodResolver(reviewSchema),
    defaultValues: { decision: "APPROVE", note: "" },
  });
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
