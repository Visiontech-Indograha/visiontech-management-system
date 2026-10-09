import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { QueryState } from "@/components/molecules/QueryState";
import { Button } from "@/components/atoms/Button";
import { TextAreaField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/molecules/PageHeader";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import {
  useDriverOptions,
  useRevisePlan,
  usePlanDetail,
  usePlanFormOptions,
  useSavePlanDraft,
  type PlanDetail,
  type PlanDraftRequest,
} from "../workPlanService";
import { useWorkTypes } from "@/features/work-types/workTypeService";
import { PendingRequestCard } from "../components/PlanRevisionPanel";
import { usePlanChanges } from "../planChangeService";
import { NewSiteDialog, type NewSite } from "../components/NewSiteDialog";
import { PlanDayTable } from "../components/PlanDayTable";
import { weekday } from "../weekday";

const required = (msg: string) => z.string().trim().min(1, msg);
const fileSchema = z.object({ file_id: z.string(), file_name: z.string() });
const taskSchema = z.object({
  title: required("Judul pekerjaan wajib diisi."),
  description: required("Deskripsi pekerjaan wajib diisi."),
  files: z.array(fileSchema),
});
const schema = z
  .object({
    title: required("Judul pekerjaan wajib diisi."),
    description: required("Deskripsi pekerjaan keseluruhan wajib diisi."),
    category: required("Pilih kategori pekerjaan."),
    site_id: z.string(),
    period_start: required("Tanggal mulai wajib diisi."),
    period_end: required("Tanggal selesai wajib diisi."),
    days: z.array(
      z.object({
        work_date: z.string(),
        tasks: z.array(taskSchema).min(1, "Isi minimal satu detail pekerjaan."),
        site_id: z.string(), // "" = ikut lokasi rencana
        work_type_id: z.string(), // "" = ikut jenis rencana
        member_mode: z.enum(["all", "custom"]), // all = seluruh tim; custom = hanya yang dipilih (ketua selalu ikut)
        member_ids: z.array(z.string()),
      }),
    ),
    holidays: z.array(z.string()), // tanggal dalam rentang yang diliburkan (dikeluarkan dari rencana)
    tool_ids: z.array(z.string()),
    vehicle_id: z.string(),
    leader_employee_id: required("Pilih ketua tim."),
    member_employee_ids: z.array(z.string()),
    driver_employee_id: z.string(),
    is_out_of_town: z.boolean(),
    work_type_id: z.string(),
    one_day: z.boolean(),
  })
  .refine((v) => v.period_end >= v.period_start, {
    path: ["period_end"],
    message: "Tanggal selesai tidak boleh sebelum tanggal mulai.",
  })
  .refine((v) => !v.vehicle_id || v.driver_employee_id.length > 0, { path: ["driver_employee_id"], message: "Pilih driver kendaraan." });
export type Values = z.infer<typeof schema>;
export type TaskValue = Values["days"][number]["tasks"][number];

const emptyTask = (): TaskValue => ({ title: "", description: "", files: [] });
type DayValue = Values["days"][number];
const newDay = (work_date: string, tasks: TaskValue[] = [emptyTask()]): DayValue => ({
  work_date,
  tasks,
  site_id: "",
  work_type_id: "",
  member_mode: "custom",
  member_ids: [],
});
/** Hari baru meniru hari pertama (judul, deskripsi, jenis, lokasi, pekerja); foto/berkas sengaja dikosongkan. */
const cloneFirstDay = (first: DayValue | undefined, work_date: string): DayValue => ({
  ...newDay(
    work_date,
    first && first.tasks.some((t) => t.title.trim())
      ? first.tasks.map((t) => ({ title: t.title, description: t.description, files: [] }))
      : [emptyTask()],
  ),
  ...(first ? { site_id: first.site_id, work_type_id: first.work_type_id, member_ids: [...first.member_ids] } : {}),
});

/** Tanggal ISO (YYYY-MM-DD) dari awal sampai akhir, inklusif; dibatasi 366 hari agar aman. */
function datesBetween(start: string, end: string): string[] {
  if (!start || !end || end < start) return [];
  const out: string[] = [];
  const d = new Date(`${start}T00:00:00Z`);
  while (out.length < 366) {
    const iso = d.toISOString().slice(0, 10);
    if (iso > end) break;
    out.push(iso);
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** "(sibuk di rencana lain: 10, 11 Okt)" — tanggal ia sudah bertugas; bentrok hanya bila hari kerja rencana ini sama. */
const busyNote = (dates?: string[]): string =>
  dates && dates.length > 0
    ? ` (sibuk di rencana lain: ${dates.slice(0, 6).map((d) => formatDate(d)).join(", ")}${dates.length > 6 ? ", …" : ""})`
    : "";

const nextDay = (iso: string) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
};

function fromDetail(detail: PlanDetail): { values: Values; site: NewSite | null } {
  const p = detail.plan as Record<string, unknown>;
  const team = detail.team as { employee_id: string; role_in_plan: string }[];
  const assets = detail.assets as { asset_id: string; kind: string; driver_employee_id: string | null }[];
  const vehicle = assets.find((a) => a.kind === "VEHICLE");
  return {
    site: null,
    values: {
      title: String(p.title ?? ""),
      description: String(p.description ?? ""),
      category: String(p.category ?? ""),
      site_id: String(p.site_id ?? ""),
      period_start: String(p.period_start ?? ""),
      period_end: String(p.period_end ?? ""),
      days: (
        detail.days as {
          work_date: string;
          site_id?: string | null;
          work_type_id?: string | null;
          member_employee_ids?: string[] | null;
          tasks: { title: string; description: string; files: TaskValue["files"] }[];
        }[]
      ).map((d) => ({
        work_date: d.work_date,
        tasks: d.tasks.map((t) => ({ title: t.title, description: t.description, files: t.files ?? [] })),
        site_id: d.site_id ? String(d.site_id) : "",
        work_type_id: d.work_type_id ? String(d.work_type_id) : "",
        member_mode: "custom" as const,
        member_ids: (d.member_employee_ids ?? team.filter((m) => m.role_in_plan === "MEMBER").map((m) => m.employee_id)).filter(
          (m) => m !== team.find((x) => x.role_in_plan === "LEADER")?.employee_id,
        ),
      })),
      holidays: datesBetween(String(p.period_start ?? ""), String(p.period_end ?? "")).filter(
        (iso) => !(detail.days as { work_date: string }[]).some((d) => d.work_date === iso),
      ),
      tool_ids: assets.filter((a) => a.kind === "TOOL").map((a) => a.asset_id),
      vehicle_id: vehicle?.asset_id ?? "",
      leader_employee_id: team.find((m) => m.role_in_plan === "LEADER")?.employee_id ?? "",
      member_employee_ids: team.filter((m) => m.role_in_plan === "MEMBER").map((m) => m.employee_id),
      driver_employee_id: vehicle?.driver_employee_id ?? "",
      is_out_of_town: p.is_out_of_town === true,
      work_type_id: String(p.work_type_id ?? ""),
      one_day: !!p.period_start && p.period_start === p.period_end,
    },
  };
}

/** Halaman "Buat SK" (/work-plans/new) dan "Ubah isi SK" (/work-plans/:id/edit) — flowchart SK2-A/B. */
export function PlanEditorPage() {
  const params = useParams();
  const [search] = useSearchParams();
  const revise = useLocation().pathname.endsWith("/revise") || Boolean(params.changeId);
  const changeId = params.changeId ?? search.get("change") ?? undefined;
  const id = params.id;
  const detail = usePlanDetail(id ?? "", Boolean(id));
  if (!id) return <PlanEditor />;
  const status = detail.data?.plan.status;
  const editable = revise ? ["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS"].includes(String(status)) : status === "DRAFT";
  return (
    <>
      <PageHeader title={revise ? "Revisi rencana kerja" : "Ubah isi rencana kerja"} />
      {revise && (
        <p className="mb-4 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">
          {status === "IN_PROGRESS"
            ? "Rencana kerja sedang berjalan: hari yang laporannya sudah dikirim/disetujui tidak berubah dan tanggal mulai tetap. "
            : ""}
          Setelah disimpan, dokumen versi baru terbit dengan tanda tangan Anda.{" "}
          {status === "PUBLISHED" || status === "APPEALED"
            ? "Ketua tim masih perlu menerimanya sekali."
            : "Versi baru langsung berlaku; ketua dan anggota mendapat pemberitahuan."}
        </p>
      )}
      {revise && <PendingRequests planId={id} />}
      <QueryState query={detail} errorText="Rencana Kerja tidak ditemukan atau Anda tidak berwenang mengubahnya.">
        {detail.data &&
          (editable ? (
            <PlanEditor planId={id} detail={detail.data} revise={revise} changeId={changeId} />
          ) : (
            <p className="text-sm text-mist">Isi rencana kerja tidak dapat diubah pada tahap ini.</p>
          ))}
      </QueryState>
    </>
  );
}

/** Permintaan revisi ketua yang masih menunggu: tampil di atas editor agar PM menjawabnya; menyimpan revisi = menyetujui. */
function PendingRequests({ planId }: { planId: string }) {
  const changes = usePlanChanges(planId);
  const pending = (changes.data ?? []).filter((c) => c.change_type === "AMENDMENT" && c.status === "PENDING_PM");
  if (pending.length === 0) return null;
  return (
    <div className="mb-4 space-y-3">
      {pending.map((c) => (
        <PendingRequestCard key={c.id} c={c}>
          <p className="mt-2 text-sm font-medium text-ink">Menyimpan revisi ini otomatis menyetujui permintaan di atas.</p>
        </PendingRequestCard>
      ))}
    </div>
  );
}

function PlanEditor({ planId, detail, revise = false, changeId }: { planId?: string; detail?: PlanDetail; revise?: boolean; changeId?: string }) {
  const navigate = useNavigate();
  const options = usePlanFormOptions(planId);
  const draftSave = useSavePlanDraft(planId);
  const revisePlan = useRevisePlan(planId ?? "");
  const [reviseReason, setReviseReason] = useState("");
  const save = revise ? { mutateAsync: (body: PlanDraftRequest) => revisePlan.mutateAsync({ ...body, reason: reviseReason.trim(), change_id: changeId ?? null }), isPending: revisePlan.isPending } : draftSave;
  const initial = useMemo(() => (detail ? fromDetail(detail) : null), [detail]);
  const [newSite, setNewSite] = useState<NewSite | null>(initial?.site ?? null);
  const [siteDialog, setSiteDialog] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: initial?.values ?? {
      title: "",
      description: "",
      category: "",
      site_id: "",
      period_start: "",
      period_end: "",
      days: [],
      holidays: [],
      tool_ids: [],
      vehicle_id: "",
      leader_employee_id: "",
      member_employee_ids: [],
      driver_employee_id: "",
      is_out_of_town: false,
      work_type_id: "",
      one_day: false,
    },
  });
  const workTypes = useWorkTypes();
  const days = useFieldArray({ control, name: "days" });
  const oneDay = useWatch({ control, name: "one_day" });
  const startDate = useWatch({ control, name: "period_start" });
  useEffect(() => {
    if (oneDay && startDate) setValue("period_end", startDate);
  }, [oneDay, startDate, setValue]);
  const [start, end, leader, members, vehicle, siteId, holidays] = useWatch({
    control,
    name: ["period_start", "period_end", "leader_employee_id", "member_employee_ids", "vehicle_id", "site_id", "holidays"],
  });

  // Rentang tanggal (dikurangi hari libur) → daftar hari; hari yang sudah diisi tetap dipertahankan, hari baru
  // meniru isi hari pertama (tanpa foto/berkas).
  useEffect(() => {
    const inRange = new Set(datesBetween(start, end));
    const off = holidays.filter((h) => inRange.has(h) && h !== start && h !== end);
    if (off.length !== holidays.length) setValue("holidays", off);
    const wanted = datesBetween(start, end).filter((d) => !off.includes(d));
    const current = getValues("days");
    if (wanted.length === current.length && wanted.every((d, i) => current[i]?.work_date === d)) return;
    const byDate = new Map(current.map((d) => [d.work_date, d]));
    const first = current[0];
    days.replace(wanted.map((d) => byDate.get(d) ?? cloneFirstDay(first, d)));
  }, [start, end, holidays]); // eslint-disable-line react-hooks/exhaustive-deps -- `days`/`getValues` stabil

  const markHoliday = (iso: string) => setValue("holidays", [...getValues("holidays"), iso].sort());
  const revokeHoliday = (iso: string) => setValue("holidays", getValues("holidays").filter((h) => h !== iso));
  /** Samakan semua hari dengan hari pertama: detail pekerjaan, jenis, lokasi, pekerja (foto/berkas tidak disalin). */
  const copyFirstToAll = () => {
    const first = getValues("days")[0];
    if (!first) return;
    getValues("days").forEach((_, i) => {
      if (i === 0) return;
      setValue(`days.${i}.tasks`, first.tasks.map((t) => ({ title: t.title, description: t.description, files: [] })));
      setValue(`days.${i}.work_type_id`, first.work_type_id);
      setValue(`days.${i}.site_id`, first.site_id);
      setValue(`days.${i}.member_mode`, "custom");
      setValue(`days.${i}.member_ids`, [...first.member_ids]);
    });
    toast.success("Semua hari disamakan dengan hari pertama (tanpa foto/berkas).");
  };

  // Tim rencana = gabungan pekerja yang dipilih per hari (untuk calon driver & ringkasan tim).
  const dayRows = useWatch({ control, name: "days" });
  useEffect(() => {
    const union = [...new Set((dayRows ?? []).flatMap((d) => d.member_ids ?? []))].filter((m) => m !== leader);
    const cur = getValues("member_employee_ids");
    if (union.length !== cur.length || union.some((u) => !cur.includes(u))) setValue("member_employee_ids", union);
  }, [dayRows, leader, getValues, setValue]);

  // Ketua tidak boleh sekaligus anggota.
  useEffect(() => {
    if (leader && members.includes(leader)) setValue("member_employee_ids", members.filter((m) => m !== leader));
  }, [leader, members, setValue]);

  const candidates = useMemo(() => [leader, ...members].filter(Boolean), [leader, members]);
  const drivers = useDriverOptions({ vehicleId: vehicle, periodEnd: end, candidates, planId });
  const people = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of [...(options.data?.leaders ?? []), ...(options.data?.members ?? [])]) map.set(String(p.id), p.full_name);
    return map;
  }, [options.data]);

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    if (!v.site_id && !newSite) return setFormError("Pilih lokasi kerja atau tambahkan lokasi baru.");
    if (revise && !reviseReason.trim()) return setFormError("Alasan revisi wajib diisi.");
    const body: PlanDraftRequest = {
      title: v.title,
      description: v.description,
      category: v.category as PlanDraftRequest["category"],
      site_id: v.site_id && v.site_id !== "__new" ? v.site_id : null,
      new_site: v.site_id === "__new" || (!v.site_id && newSite) ? newSite : null,
      period_start: v.period_start,
      period_end: v.period_end,
      days: v.days.map((d) => ({
        work_date: d.work_date,
        tasks: d.tasks.map((t) => ({ title: t.title, description: t.description, file_ids: t.files.map((f) => f.file_id) })),
        site_id: d.site_id || null,
        work_type_id: d.work_type_id || null,
        member_employee_ids: d.member_mode === "custom" ? d.member_ids.filter((m) => m !== v.leader_employee_id) : null,
      })),
      leader_employee_id: v.leader_employee_id,
      member_employee_ids: [...new Set([...v.member_employee_ids, ...v.days.flatMap((d) => (d.member_mode === "custom" ? d.member_ids : []))])].filter(
        (m) => m !== v.leader_employee_id,
      ),
      is_out_of_town: v.is_out_of_town,
      work_type_id: v.work_type_id || null,
      tool_ids: v.tool_ids,
      vehicle_id: v.vehicle_id || null,
      driver_employee_id: v.vehicle_id ? v.driver_employee_id : null,
      row_version: detail ? Number(detail.plan.row_version) : null,
    };
    try {
      const saved = await save.mutateAsync(body);
      toast.success(revise ? "Revisi disimpan dan ditandatangani." : planId ? "Isi rencana kerja disimpan." : "Rencana Kerja tersimpan sebagai Draf.");
      navigate(`/work-plans/${String(saved.plan.id)}`);
    } catch (err) {
      setFormError(errorMessage(err));
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  const o = options.data;
  return (
    <>
      {!planId && <PageHeader title="Buat rencana kerja" />}
      <QueryState query={options} errorText="Pilihan form rencana kerja tidak dapat dimuat.">
        {o && (
          <form onSubmit={onSubmit} noValidate className="space-y-6 pb-24">
            {formError && (
              <p role="alert" className="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
                {formError}
              </p>
            )}
            {revise && (
              <Section title="Alasan revisi">
                <p className="mb-2 text-sm text-mist">
                  Alasan ini dikirim ke ketua dan anggota, dan tercatat di riwayat revisi. Jelaskan apa yang diubah dan mengapa.
                </p>
                <TextAreaField
                  label="Alasan revisi (wajib)"
                  placeholder="Contoh: Jadwal hari ke-2 dimajukan karena material tiba lebih awal."
                  value={reviseReason}
                  onChange={(e) => setReviseReason(e.target.value)}
                />
              </Section>
            )}
            <Section title="Data rencana kerja">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] border-collapse text-sm">
                  <tbody>
                    <Row label="Jenis pekerjaan" hint="Pilih lebih dulu: menentukan template foto laporan (foto contoh dari PM). Bisa diganti per hari di tabel hari kerja.">
                      <select aria-label="Jenis pekerjaan" className={inputCls} {...register("work_type_id")}>
                        <option value="">Tanpa jenis</option>
                        {workTypes.data?.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </Row>
                    <Row label="Judul pekerjaan" error={errors.title?.message}>
                      <input aria-label="Judul pekerjaan" className={inputCls} {...register("title")} />
                    </Row>
                    <Row label="Deskripsi pekerjaan" error={errors.description?.message}>
                      <textarea aria-label="Deskripsi pekerjaan" rows={3} className={`${inputCls} h-auto py-2`} {...register("description")} />
                    </Row>
                    <Row label="Kategori" error={errors.category?.message}>
                      <select aria-label="Kategori pekerjaan" className={inputCls} {...register("category")}>
                        <option value="">Pilih kategori</option>
                        {o.categories.map((c) => (
                          <option key={c.code} value={c.code}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </Row>
                    <Row label="Tipe" hint="Otomatis mengikuti unit PM.">
                      <span>{o.unit_name ?? "-"}</span>
                    </Row>
                    <Row label="Tanggal" error={errors.period_start?.message ?? errors.period_end?.message}>
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          type="date"
                          aria-label="Tanggal mulai"
                          className={`${inputCls} w-auto`}
                          readOnly={revise && detail?.plan.status === "IN_PROGRESS"}
                          {...register("period_start")}
                        />
                        {!oneDay && (
                          <>
                            <span>s.d.</span>
                            <input type="date" aria-label="Tanggal selesai" className={`${inputCls} w-auto`} {...register("period_end")} />
                          </>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-x-4">
                        <label className="flex min-h-11 items-center gap-2">
                          <input type="checkbox" className="size-5" {...register("one_day")} /> Rencana kerja 1 hari
                        </label>
                        <label className="flex min-h-11 items-center gap-2">
                          <input type="checkbox" className="size-5" {...register("is_out_of_town")} /> Luar kota (uang absen luar kota)
                        </label>
                      </div>
                    </Row>
                    <Row label="Lokasi" hint="Lokasi utama; bisa diganti per hari di tabel hari kerja.">
                      <select
                        aria-label="Lokasi kerja"
                        className={inputCls}
                        {...register("site_id", {
                          onChange: (e: React.ChangeEvent<HTMLSelectElement>) => {
                            if (e.target.value === "__new") setSiteDialog(true);
                          },
                        })}
                      >
                        <option value="">Pilih lokasi yang sudah ada</option>
                        {o.sites.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                        <option value="__new">+ Lokasi baru{newSite ? `: ${newSite.name}` : ""}</option>
                      </select>
                      {siteId === "__new" && newSite && (
                        <p className="mt-1 text-mist">
                          {newSite.name} · {newSite.lat.toFixed(6)}, {newSite.lng.toFixed(6)}{" "}
                          <button type="button" className="min-h-11 text-lens" onClick={() => setSiteDialog(true)}>
                            Ubah
                          </button>
                        </p>
                      )}
                    </Row>
                    <Row label="Ketua tim" error={errors.leader_employee_id?.message} hint="Ketua bertugas di semua hari.">
                      <select aria-label="Ketua tim" className={inputCls} {...register("leader_employee_id")}>
                        <option value="">Pilih ketua tim</option>
                        {o.leaders.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.full_name} — {p.position}
                            {busyNote(p.busy_dates)}
                          </option>
                        ))}
                      </select>
                    </Row>
                    <Row label="Anggota (gabungan)" hint="Dipilih per hari di tabel hari kerja di bawah.">
                      <span>{members.length ? members.map((m) => people.get(m) ?? m).join(", ") : "Belum ada anggota"}</span>
                    </Row>
                    <Row label="Alat">
                      {o.tools.length === 0 ? (
                        <span className="text-mist">Tidak ada alat yang siap pakai.</span>
                      ) : (
                        <div className="flex max-h-40 flex-wrap gap-x-4 overflow-y-auto">
                          {o.tools.map((t) => (
                            <label key={t.id} className="flex min-h-11 items-center gap-2">
                              <input type="checkbox" className="size-5" value={t.id} {...register("tool_ids")} />
                              {t.name} · {t.code}
                            </label>
                          ))}
                        </div>
                      )}
                    </Row>
                    <Row label="Kendaraan" hint="Opsional. Hanya kendaraan siap pakai yang tidak terikat rencana lain.">
                      <select aria-label="Kendaraan" className={inputCls} {...register("vehicle_id")}>
                        <option value="">Tanpa kendaraan</option>
                        {o.vehicles.map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.name} · {v.code} ({v.vehicle_type === "MOTORCYCLE" ? "roda dua, SIM C" : "SIM A"})
                          </option>
                        ))}
                      </select>
                    </Row>
                    {vehicle && (
                      <Row
                        label="Driver"
                        error={errors.driver_employee_id?.message}
                        hint={
                          candidates.length === 0
                            ? "Pilih ketua/anggota dulu."
                            : drivers.data && drivers.data.length === 0
                              ? "Tidak ada ketua/anggota dengan SIM yang sesuai tipe kendaraan."
                              : "Ketua atau anggota terpilih dengan SIM sesuai tipe kendaraan."
                        }
                      >
                        <select aria-label="Driver" className={inputCls} {...register("driver_employee_id")}>
                          <option value="">{drivers.isFetching ? "Memuat..." : "Pilih driver"}</option>
                          {drivers.data?.map((d) => (
                            <option key={d} value={d}>
                              {people.get(d) ?? d}
                            </option>
                          ))}
                        </select>
                      </Row>
                    )}
                  </tbody>
                </table>
              </div>
            </Section>

            <Section title="Hari kerja">
              {days.fields.length === 0 ? (
                <p className="text-sm text-mist">Isi tanggal di atas; baris hari kerja akan muncul di tabel ini.</p>
              ) : (
                <PlanDayTable
                  fields={days.fields}
                  control={control}
                  register={register}
                  setValue={setValue}
                  errors={errors}
                  sites={o.sites}
                  workTypes={(workTypes.data ?? []).map((t) => ({ id: t.id, name: t.name }))}
                  candidates={(o.members ?? [])
                    .filter((p) => String(p.id) !== leader)
                    .map((p) => ({ id: String(p.id), name: p.full_name, busy: p.busy_dates ?? [] }))}
                  onHoliday={markHoliday}
                />
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {days.fields.length > 1 && (
                  <Button type="button" variant="outline" onClick={copyFirstToAll}>
                    Samakan semua hari dengan hari pertama
                  </Button>
                )}
                {end && !oneDay && (
                  <Button type="button" variant="outline" onClick={() => setValue("period_end", nextDay(end))}>
                    <Plus className="size-4" /> Tambah hari kerja
                  </Button>
                )}
              </div>
              {holidays.length > 0 && (
                <div className="mt-3 rounded-control border border-line p-3" aria-label="Hari libur">
                  <p className="mb-2 text-sm font-medium">Hari libur ({holidays.length})</p>
                  <ul className="space-y-1">
                    {holidays.map((h) => (
                      <li key={h} className="flex items-center justify-between gap-2 text-sm">
                        <span>
                          {weekday(h)}, {formatDate(h)}
                        </span>
                        <Button type="button" variant="outline" size="sm" onClick={() => revokeHoliday(h)}>
                          Jadikan hari kerja
                        </Button>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-mist">Hari libur tidak wajib absen dan laporan. Hari yang sudah berlaporan tidak dapat diliburkan.</p>
                </div>
              )}
            </Section>

            <div className="sticky bottom-0 -mx-4 flex gap-3 border-t border-line bg-surface px-4 py-3 md:mx-0 md:rounded-panel md:border">
              <Button type="button" variant="outline" className="flex-1 md:flex-none" asChild>
                <Link to={planId ? `/work-plans/${planId}` : "/work-plans"}>Batal</Link>
              </Button>
              <Button type="submit" className="flex-1 md:flex-none" disabled={isSubmitting}>
                {isSubmitting ? "Menyimpan..." : "Simpan"}
              </Button>
            </div>
          </form>
        )}
      </QueryState>
      {siteDialog && (
        <NewSiteDialog
          initial={newSite}
          onClose={() => {
            setSiteDialog(false);
            if (!newSite) setValue("site_id", "");
          }}
          onSave={(s) => {
            setNewSite(s);
            setValue("site_id", "__new");
            setSiteDialog(false);
          }}
        />
      )}
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="rounded-panel border border-line bg-surface p-4 shadow-card md:p-5">
      <h2 className="mb-4 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

const inputCls =
  "h-11 w-full rounded-md border border-input bg-transparent px-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

/** Satu baris tabel data rencana: label di kiri, isian di kanan, bantuan/galat di bawah isian. */
function Row({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-line">
      <th scope="row" className="w-48 py-3 pr-3 text-left align-top font-medium">
        {label}
      </th>
      <td className="py-2">
        {children}
        {error ? <p className="mt-1 text-xs text-destructive">{error}</p> : hint ? <p className="mt-1 text-xs text-mist">{hint}</p> : null}
      </td>
    </tr>
  );
}
