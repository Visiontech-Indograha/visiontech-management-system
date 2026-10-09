import { zodResolver } from "@hookform/resolvers/zod";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/atoms/Button";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/molecules/PageHeader";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { formatDate, formatDateTime } from "@/lib/format";
import { STATUS_LABEL } from "@/lib/labels";
import { FilePreview } from "@/components/molecules/FilePreview";
import { OfficeCheckInCard } from "./OfficeCheckInCard";

type Attendance = components["schemas"]["AttendanceResponse"];
type AttendanceList = components["schemas"]["AttendanceListResponse"];
const STATUSES = ["NEEDS_REVIEW", "AUTO_VALID", "APPROVED", "REJECTED"];
const PAGE_SIZE = 50;
const selectCls = "h-11 w-full rounded-control border border-line bg-surface px-3 text-sm";

interface Filters {
  status: string;
  from: string;
  to: string;
  page: number;
  /** mine = absensi pribadi, team = absensi anggota/umum, kosong = bawaan lama (tanpa pemisahan). */
  scope: "mine" | "team" | "";
}

function useAttendance(f: Filters) {
  return useQuery({
    queryKey: ["attendance", f],
    queryFn: async () =>
      (
        await api.get<AttendanceList>("/attendance", {
          params: {
            page: f.page,
            size: PAGE_SIZE,
            ...(f.scope ? { scope: f.scope } : {}),
            ...(f.status ? { status: f.status } : {}),
            ...(f.from ? { from: f.from } : {}),
            ...(f.to ? { to: f.to } : {}),
          },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}

function useAttendanceAction<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["attendance"] });
      await qc.invalidateQueries({ queryKey: ["attendance-recap"] });
    },
  });
}

/**
 * Daftar absensi (GET /attendance) — prototype/js/operations.js attendance(). Cakupan data diatur API (R-33):
 * Finance & OPS seluruh organisasi; PM miliknya + bawahan lapangan di unitnya; lainnya milik sendiri.
 * Tombol Tinjau hanya bila server menandai `can_review` (PM → bawahan, Finance → kantor, OPS → Finance).
 * Absen masuk/pulang: pekerja kantor di sini (OfficeCheckInCard), pekerja lapangan di aplikasi HP.
 */
export function AttendancePage() {
  const { me } = useSession();
  const canReview = !!me?.permissions.includes("review:attendance");
  // Pemegang wewenang lihat/tinjau absensi orang lain: pisahkan absensi pribadi dari absensi anggota (PM) / umum (Finance, OPS).
  const sees = !!me?.permissions.includes("view:all_attendance");
  const hasTeam = canReview || sees;
  const teamLabel = sees ? "Absensi umum" : "Absensi anggota";
  const [f, setF] = useState<Filters>({
    status: canReview ? "NEEDS_REVIEW" : "", from: "", to: "", page: 1, scope: hasTeam ? "team" : "",
  });
  const list = useAttendance(f);
  const [open, setOpen] = useState<{ kind: "review" | "explain"; item: Attendance } | null>(null);
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const set = (patch: Partial<Filters>) => setF((old) => ({ ...old, ...patch, page: patch.page ?? 1 }));

  return (
    <>
      <PageHeader title="Absensi" />
      <OfficeCheckInCard />
      {hasTeam && (
        <div role="tablist" aria-label="Jenis absensi" className="mb-4 inline-flex rounded-control border border-line bg-surface p-1">
          {([["mine", "Absensi saya"], ["team", teamLabel]] as const).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              type="button"
              aria-selected={f.scope === key}
              className={`min-h-10 rounded-control px-4 text-sm font-medium ${f.scope === key ? "bg-primary text-primary-foreground" : "text-mist hover:bg-muted"}`}
              onClick={() => setF((old) => ({ ...old, scope: key, status: key === "team" && canReview ? "NEEDS_REVIEW" : "", page: 1 }))}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="mb-4 grid gap-x-3 md:grid-cols-3">
        <div className="mb-4 space-y-1.5">
          <label htmlFor="att-status" className="text-sm font-medium">
            Status
          </label>
          <select id="att-status" className={selectCls} value={f.status} onChange={(e) => set({ status: e.target.value })}>
            <option value="">Semua status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
        <TextField label="Dari tanggal" type="date" value={f.from} onChange={(e) => set({ from: e.target.value })} />
        <TextField label="Sampai tanggal" type="date" value={f.to} onChange={(e) => set({ to: e.target.value })} />
      </div>

      <QueryState query={list} errorText="Absensi tidak dapat dimuat." empty={data?.items.length === 0} emptyText="Tidak ada catatan kehadiran yang cocok.">
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data?.items.map((a) => (
            <li key={a.id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{a.employee_name ?? "-"}</p>
                  <p className="text-sm text-mist">
                    {formatDate(a.work_date)} · {a.site_label}
                  </p>
                </div>
                <StatusBadge status={a.status} />
              </div>
              <dl className="text-sm">
                <div>
                  <dt className="inline text-mist">Masuk / keluar: </dt>
                  <dd className="inline">
                    {formatDateTime(a.check_in_at)} / {a.check_out_at ? formatDateTime(a.check_out_at) : "belum keluar"}
                  </dd>
                </div>
                <div>
                  <dt className="inline text-mist">Jarak: </dt>
                  <dd className="inline">
                    {Math.round(a.distance_m)} m{a.is_late ? " · terlambat" : ""}
                    {a.is_early_leave ? " · pulang cepat" : ""}
                    {a.offline ? " · absen luring" : ""}
                    {a.city_category === "LUAR_KOTA" ? " · luar kota" : " · dalam kota"}
                  </dd>
                </div>
                {a.check_out_distance_m != null && (
                  <div>
                    <dt className="inline text-mist">Jarak pulang: </dt>
                    <dd className="inline">
                      {Math.round(a.check_out_distance_m)} m{a.check_out_outside ? " · Pulang di luar radius" : ""}
                    </dd>
                  </div>
                )}
                {(a.face_result || a.check_out_face_result) && (
                  <div>
                    <dt className="inline text-mist">Wajah: </dt>
                    <dd className="inline">
                      {a.face_result
                        ? `Masuk: ${a.face_result}${a.face_similarity !== null && a.face_similarity !== undefined ? ` (${Math.round(a.face_similarity * 100)}%)` : ""}`
                        : ""}
                      {a.face_result && a.check_out_face_result ? " · " : ""}
                      {a.check_out_face_result
                        ? `Pulang: ${a.check_out_face_result}${a.check_out_face_similarity !== null && a.check_out_face_similarity !== undefined ? ` (${Math.round(a.check_out_face_similarity * 100)}%)` : ""}`
                        : ""}
                    </dd>
                  </div>
                )}
                {a.explanation && (
                  <div>
                    <dt className="inline text-mist">Penjelasan: </dt>
                    <dd className="inline">{a.explanation}</dd>
                  </div>
                )}
                <div className="text-mist">
                  {a.status === "AUTO_VALID"
                    ? "Tidak perlu ditinjau · jarak dalam radius"
                    : a.status === "NEEDS_REVIEW"
                      ? "Menunggu pemeriksaan"
                      : `Ditinjau ${a.reviewed_at ? formatDateTime(a.reviewed_at) : ""}`}
                </div>
              </dl>
              {a.status === "NEEDS_REVIEW" && (
                <div className="mt-auto flex flex-col gap-2 md:flex-row">
                  {a.can_review ? (
                    <Button onClick={() => setOpen({ kind: "review", item: a })}>Tinjau</Button>
                  ) : a.employee_id === me?.employee_id ? (
                    <Button variant="outline" onClick={() => setOpen({ kind: "explain", item: a })}>
                      {a.explanation ? "Ubah penjelasan" : "Beri penjelasan"}
                    </Button>
                  ) : null}
                </div>
              )}
            </li>
          ))}
        </ul>
        {data && data.total > data.size && (
          <nav aria-label="Halaman" className="mt-4 flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
            <span className="text-mist">
              {data.total} catatan · halaman {data.page} dari {lastPage}
            </span>
            <span className="flex gap-2">
              <Button variant="outline" disabled={f.page <= 1} onClick={() => set({ page: f.page - 1 })}>
                Sebelumnya
              </Button>
              <Button variant="outline" disabled={f.page >= lastPage} onClick={() => set({ page: f.page + 1 })}>
                Berikutnya
              </Button>
            </span>
          </nav>
        )}
      </QueryState>

      {open?.kind === "review" && <ReviewDialog item={open.item} onClose={() => setOpen(null)} />}
      {open?.kind === "explain" && <ExplainDialog item={open.item} onClose={() => setOpen(null)} />}
    </>
  );
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
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </Button>
          <Button type="submit" form="attendance-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </Button>
        </>
      }
    >
      <form id="attendance-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {children}
      </form>
    </VmsDialog>
  );
}

const reviewSchema = z.object({
  decision: z.enum(["APPROVE", "REJECT"]),
  note: z.string().trim().min(1, "Catatan pemeriksaan wajib diisi."),
});
type ReviewValues = z.infer<typeof reviewSchema>;

/** Finance meninjau absensi di luar radius (POST /attendance/{id}/review). */
function ReviewDialog({ item, onClose }: { item: Attendance; onClose: () => void }) {
  const review = useAttendanceAction(async (body: components["schemas"]["ReviewRequest"]) =>
    (await api.post(`/attendance/${item.id}/review`, body)).data,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReviewValues>({ resolver: zodResolver(reviewSchema), defaultValues: { decision: "APPROVE", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await review.mutateAsync({ is_approved: v.decision === "APPROVE", note: v.note });
      toast.success(v.decision === "APPROVE" ? "Absensi disetujui." : "Absensi ditolak.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Tinjau absensi" submitLabel="Simpan keputusan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <p className="mb-1 text-sm font-medium">{item.employee_name}</p>
      <p className="mb-3 text-sm text-mist">
        {item.site_label} · {Math.round(item.distance_m)} m · masuk {formatDateTime(item.check_in_at)}
      </p>
      {item.offline && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <p className="font-medium">Absen luring (direkam tanpa sinyal, dikirim saat online)</p>
          {item.offline_note && <p>Catatan server: {item.offline_note}</p>}
          {item.check_out_requested_at && (
            <p>
              Absen pulang {formatDateTime(item.check_out_requested_at)} berlaku bila absensi ini disetujui.
            </p>
          )}
        </div>
      )}
      {item.check_out_outside && (
        <div role="status" className="mb-3 rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          <p className="font-medium">
            Pulang di luar radius ({Math.round(item.check_out_distance_m ?? 0)} m dari lokasi)
          </p>
          {item.check_out_explanation && <p>Penjelasan: {item.check_out_explanation}</p>}
          {item.check_out_selfie_file_id && (
            <div className="mt-2">
              <FilePreview fileId={item.check_out_selfie_file_id} fileName="Swafoto pulang" />
            </div>
          )}
        </div>
      )}
      {item.selfie_file_id ? (
        <div className="mb-3">
          <p className="mb-1 text-sm font-medium">Swafoto</p>
          <FilePreview fileId={item.selfie_file_id} fileName="Swafoto absen" />
        </div>
      ) : (
        <p className="mb-3 text-sm text-mist">Tanpa swafoto.</p>
      )}
      {(item.face_result || item.check_out_face_result) && (
        <div role="status" className="mb-3 rounded-control border border-line bg-surface p-3 text-sm">
          <p className="font-medium">Verifikasi Wajah (Server)</p>
          {item.face_result && (
            <p className="text-mist">
              Masuk: <span className="font-medium text-foreground">{item.face_result}</span>
              {item.face_similarity !== null && item.face_similarity !== undefined
                ? ` · Kemiripan: ${(item.face_similarity * 100).toFixed(1)}%`
                : ""}
            </p>
          )}
          {item.check_out_face_result && (
            <p className="text-mist">
              Pulang: <span className="font-medium text-foreground">{item.check_out_face_result}</span>
              {item.check_out_face_similarity !== null && item.check_out_face_similarity !== undefined
                ? ` · Kemiripan: ${(item.check_out_face_similarity * 100).toFixed(1)}%`
                : ""}
            </p>
          )}
        </div>
      )}
      <p className="mb-3 text-sm">Penjelasan karyawan: {item.explanation ?? "belum diisi"}</p>
      <SelectField label="Keputusan" {...register("decision")}>
        <option value="APPROVE">Setujui</option>
        <option value="REJECT">Tolak</option>
      </SelectField>
      <TextAreaField label="Catatan pemeriksaan" error={errors.note?.message} {...register("note")} />
    </FormDialog>
  );
}

const explainSchema = z.object({ explanation: z.string().trim().min(1, "Penjelasan wajib diisi.") });

/** Karyawan memberi penjelasan atas absensi sendiri yang perlu ditinjau (POST /attendance/{id}/explain). */
function ExplainDialog({ item, onClose }: { item: Attendance; onClose: () => void }) {
  const explain = useAttendanceAction(async (body: components["schemas"]["ExplanationRequest"]) =>
    (await api.post(`/attendance/${item.id}/explain`, body)).data,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ explanation: string }>({ resolver: zodResolver(explainSchema), defaultValues: { explanation: item.explanation ?? "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await explain.mutateAsync(v);
      toast.success("Penjelasan ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Beri penjelasan" submitLabel="Kirim penjelasan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextAreaField label="Penjelasan" error={errors.explanation?.message} {...register("explanation")} />
    </FormDialog>
  );
}
