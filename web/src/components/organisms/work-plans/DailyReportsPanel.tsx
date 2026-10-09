import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFormDraft } from "@/hooks/useFormDraft";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/stores/sessionStore";
import { FilePreview } from "@/components/molecules/FilePreview";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { formatDate, formatDateTime } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { oversize, uploadFiles } from "@/services/uploadService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlInput, ControlLabel, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { DisclosureBlock, DisclosureTitle } from "@/components/molecules/DisclosureBlock";
import { listMemberReports, listPlanDays, reviewDailyReport, saveDailyReport, submitDailyReport, toggleDayTask, type DailyReportInput, type DayTask, type PlanDay, type ReportReviewInput } from "@/services/dailyReportService";
import { FormErrorText } from "@/components/molecules/FormErrorText";

type Day = PlanDay;
type Task = DayTask;
type ReportIn = DailyReportInput;
type ReviewIn = ReportReviewInput;

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
 * Laporan harian rencana kerja (GET /work-plans/{id}/days) — checklist tugas (toggle), isi & kirim laporan (ketua),
 * review PM. Tindakan ketua ditampilkan kepada semua; API menolak dengan pesan jelas bila bukan ketua.
 */
type Evidence = { file_id: string; slot_label?: string | null; source?: string };

/** Foto bukti dikelompokkan per slot template ("Foto lain" untuk yang tanpa slot); data lama hanya punya id. */
function evidenceBySlot(evidence: Evidence[] | undefined, ids: string[]): [string, Evidence[]][] {
  const list: Evidence[] = evidence && evidence.length > 0 ? evidence : ids.map((file_id) => ({ file_id }));
  const groups = new Map<string, Evidence[]>();
  for (const e of list) {
    const key = e.slot_label || "Foto lain";
    groups.set(key, [...(groups.get(key) ?? []), e]);
  }
  return [...groups.entries()];
}

export function DailyReportsPanel({ plan }: { plan: WorkPlan }) {
  const days = useQuery({
    queryKey: daysKey(plan.id),
    queryFn: () => listPlanDays(plan.id),
  });
  return (
    <section aria-label="Laporan harian" className="space-y-3">
      <TextBlock as="h2" className="text-base font-semibold">Laporan harian</TextBlock>
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

function DayPanel({ plan, day }: { plan: WorkPlan; day: Day }) {
  const { me } = useSession();
  const isPM = !!me?.permissions.includes("create:plan");
  // Alur rencana kerja v2: hanya ketua menurut rencana kerja yang mengisi laporan (di HP); PM tidak melihat form ketua (CELAH 7).
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
          <TextBlock as="h3" className="font-medium">{day.title || "Hari kerja"}</TextBlock>
          <TextBlock className="text-sm text-mist">{formatDate(day.work_date)}</TextBlock>
        </div>
        <div className="flex items-center gap-2">
          {day.report ? <StatusBadge status={badge} /> : <TextBlock as="span" className="text-sm text-mist">Belum ada laporan</TextBlock>}
          {status === "APPROVED" && (
            <ActionButton variant="outline" size="sm" onClick={() => setViewing(true)}>
              Lihat laporan
            </ActionButton>
          )}
        </div>
      </header>
      <TaskList plan={plan} day={day} editable={editable} />
      {!reached ? (
        <TextBlock className="mt-3 text-sm text-mist">Laporan dapat diisi mulai {formatDate(day.work_date)}.</TextBlock>
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
        <PlanPreviewDialog
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
    (t: Task) => toggleDayTask(plan.id, day.id, t.id),
  );
  const [error, setError] = useState<string | null>(null);
  if (day.tasks.length === 0) return <TextBlock className="text-sm text-mist">Belum ada tugas.</TextBlock>;
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
      <FormErrorText message={error} className="mb-3" />
      <ListBlock aria-label="Tugas" className="space-y-2">
        {[...day.tasks]
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((t) => (
            <ListEntry key={t.id}>
              <ControlLabel className="flex items-center gap-3 text-sm">
                <ControlInput
                  type="checkbox"
                  className="size-5"
                  checked={t.is_done}
                  disabled={!editable || toggle.isPending}
                  onChange={() => onToggle(t)}
                />
                <TextBlock as="span" className={t.is_done ? "text-mist line-through" : undefined}>{t.title}</TextBlock>
                {t.done_at && <TextBlock as="span" className="text-xs text-mist">{formatDateTime(t.done_at)}</TextBlock>}
              </ControlLabel>
            </ListEntry>
          ))}
      </ListBlock>
    </>
  );
}

/** Laporan anggota yang dikirim ke ketua (alur rencana kerja v2) — dibaca PM saat memeriksa laporan ketua. */
function MemberReports({ plan, day }: { plan: WorkPlan; day: Day }) {
  const reports = useQuery({
    queryKey: ["member-reports", day.id],
    queryFn: () => listMemberReports(plan.id, day.id),
  });
  const sent = (reports.data ?? []).filter((r) => r.status === "SENT");
  return (
    <DisclosureBlock className="mt-3 rounded-control border border-line p-3 text-sm">
      <DisclosureTitle className="cursor-pointer font-medium">Laporan anggota ({day.member_reports_sent})</DisclosureTitle>
      <ListBlock className="mt-2 space-y-2">
        {sent.map((r) => (
          <ListEntry key={r.id}>
            <TextBlock className="font-medium">
              {r.full_name} <TextBlock as="span" className="font-normal text-mist">— {r.position}</TextBlock>
            </TextBlock>
            <TextBlock className="whitespace-pre-line">{r.body}</TextBlock>
            {r.obstacle && <TextBlock className="text-mist">Kendala: {r.obstacle}</TextBlock>}
          </ListEntry>
        ))}
      </ListBlock>
    </DisclosureBlock>
  );
}

function ReportView({ day }: { day: Day }) {
  const r = day.report;
  if (!r || !r.body) return <TextBlock className="mt-3 text-sm text-mist">Belum ada laporan harian.</TextBlock>;
  return (
    <ListBlock as="dl" className="mt-3 space-y-2 text-sm">
      <div>
        <TextBlock as="dt" className="text-mist">Laporan</TextBlock>
        <TextBlock as="dd" className="whitespace-pre-line">{r.body}</TextBlock>
      </div>
      <div>
        <TextBlock as="dt" className="text-mist">Kendala</TextBlock>
        <TextBlock as="dd" className="whitespace-pre-line">{r.obstacle}</TextBlock>
      </div>
      {r.evidence_file_ids.length > 0 && (
        <div>
          <TextBlock as="dt" className="text-mist">Bukti ({r.evidence_file_ids.length} foto)</TextBlock>
          {/* PM menilai laporan dari foto bukti — tampilkan pratinjau per slot template (T9), bukan sekadar jumlah. */}
          <TextBlock as="dd" className="mt-1 space-y-2">
            {evidenceBySlot(r.evidence, r.evidence_file_ids).map(([slot, items]) => (
              <div key={slot}>
                <TextBlock className="text-xs font-medium text-mist">{slot}</TextBlock>
                <div className="flex flex-wrap gap-2">
                  {items.map((e, i) => (
                    <div key={e.file_id} className="relative">
                      <FilePreview fileId={e.file_id} fileName={`${slot} ${i + 1}`} />
                      {e.source === "GALLERY" && (
                        <TextBlock as="span" className="absolute left-1 top-1 rounded-control bg-surface/90 px-1.5 py-0.5 text-[11px] font-medium text-ink shadow-card">
                          Dari galeri
                        </TextBlock>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </TextBlock>
        </div>
      )}
      {r.review_note && (
        <div>
          <TextBlock as="dt" className="text-mist">Catatan PM</TextBlock>
          <TextBlock as="dd">{r.review_note}</TextBlock>
        </div>
      )}
    </ListBlock>
  );
}

const dailySchema = z.object({
  body: z.string().trim().min(10, "Laporan harian minimal 10 karakter."),
  obstacle: z.string().trim().min(1, 'Kendala wajib diisi (isi "Tidak ada" jika lancar).'),
});
type DailyValues = z.infer<typeof dailySchema>;

/** Ketua menyimpan (PUT /days/{day}) lalu mengirim (POST submit); bukti diunggah ke /files/upload dulu. */
function DailyForm({ plan, day }: { plan: WorkPlan; day: Day }) {
  const save = useDayMutation(plan.id, (body: ReportIn) => saveDailyReport(plan.id, day.id, body));
  const submit = useDayMutation<void>(plan.id, () => submitDailyReport(plan.id, day.id));
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
    <FormBlock noValidate onSubmit={send(true)} className="mt-4 border-t border-line pt-4">
      <FormErrorText message={formError} />
      {day.report?.review_note && <TextBlock className="mb-3 text-sm text-warning">Catatan PM: {day.report.review_note}</TextBlock>}
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
  .refine((v) => v.decision === "APPROVE" || v.note.length > 0, {
    path: ["note"],
    message: "Catatan revisi wajib diisi.",
  });
type ReviewValues = z.infer<typeof reviewSchema>;

function DailyReviewForm({ plan, day }: { plan: WorkPlan; day: Day }) {
  const review = useDayMutation(
    plan.id,
    (body: ReviewIn) => reviewDailyReport(plan.id, day.id, body),
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
    <FormBlock noValidate onSubmit={onSubmit} className="mt-4 border-t border-line pt-4">
      <FormErrorText message={formError} />
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
