import { zodResolver } from "@hookform/resolvers/zod";
import { Paperclip, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm, useWatch, type Control, type FieldErrors, type UseFormRegister, type UseFormSetValue } from "react-hook-form";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { QueryState } from "@/components/molecules/QueryState";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField, TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
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
} from "./api";
import { useWorkTypes } from "@/features/work-types/api";
import { PendingRequestCard } from "./AmendmentPanel";
import { usePlanChanges } from "./plan-changes";
import { NewSiteDialog, type NewSite } from "./NewSiteDialog";
import { oversize, uploadFiles } from "./uploads";

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
type Values = z.infer<typeof schema>;
type TaskValue = Values["days"][number]["tasks"][number];

const emptyTask = (): TaskValue => ({ title: "", description: "", files: [] });
type DayValue = Values["days"][number];
const newDay = (work_date: string, tasks: TaskValue[] = [emptyTask()]): DayValue => ({
  work_date,
  tasks,
  site_id: "",
  member_mode: "all",
  member_ids: [],
});
/** Hari baru meniru isi hari pertama (judul + deskripsi); foto/berkas sengaja dikosongkan. Lokasi/anggota ikut rencana. */
const cloneFirstDay = (first: DayValue | undefined, work_date: string): DayValue =>
  newDay(
    work_date,
    first && first.tasks.some((t) => t.title.trim())
      ? first.tasks.map((t) => ({ title: t.title, description: t.description, files: [] }))
      : [emptyTask()],
  );

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
          member_employee_ids?: string[] | null;
          tasks: { title: string; description: string; files: TaskValue["files"] }[];
        }[]
      ).map((d) => ({
        work_date: d.work_date,
        tasks: d.tasks.map((t) => ({ title: t.title, description: t.description, files: t.files ?? [] })),
        site_id: d.site_id ? String(d.site_id) : "",
        member_mode: d.member_employee_ids ? "custom" : "all",
        member_ids: (d.member_employee_ids ?? []).filter((m) => m !== team.find((x) => x.role_in_plan === "LEADER")?.employee_id),
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
  /** Samakan judul + deskripsi semua hari dengan hari pertama (foto/berkas, lokasi, dan anggota hari lain tidak diubah). */
  const copyFirstToAll = () => {
    const first = getValues("days")[0];
    if (!first) return;
    getValues("days").forEach((_, i) => {
      if (i > 0) setValue(`days.${i}.tasks`, first.tasks.map((t) => ({ title: t.title, description: t.description, files: [] })));
    });
    toast.success("Judul dan deskripsi hari lain disamakan dengan hari pertama.");
  };

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
        member_employee_ids: d.member_mode === "custom" ? d.member_ids.filter((m) => v.member_employee_ids.includes(m)) : null,
      })),
      leader_employee_id: v.leader_employee_id,
      member_employee_ids: v.member_employee_ids,
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
            <Section title="Data pekerjaan">
              <SelectField label="Jenis pekerjaan" hint="Pilih lebih dulu: menentukan template foto laporan (foto contoh dari PM)." {...register("work_type_id")}>
                <option value="">Tanpa jenis</option>
                {workTypes.data?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </SelectField>
              <TextField label="Judul pekerjaan" error={errors.title?.message} {...register("title")} />
              <TextAreaField label="Deskripsi pekerjaan keseluruhan" error={errors.description?.message} {...register("description")} />
              <div className="grid gap-x-3 md:grid-cols-2">
                <SelectField label="Kategori pekerjaan" error={errors.category?.message} {...register("category")}>
                  <option value="">Pilih kategori</option>
                  {o.categories.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label}
                    </option>
                  ))}
                </SelectField>
                <TextField label="Tipe" value={o.unit_name ?? "-"} readOnly disabled hint="Otomatis mengikuti unit PM." />
              </div>
            </Section>

            <Section title="Lokasi kerja">
              <SelectField
                label="Lokasi kerja"
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
              </SelectField>
              {siteId === "__new" && newSite && (
                <div className="rounded-control border border-line bg-canvas px-3 py-2 text-sm">
                  <p className="font-medium">{newSite.name}</p>
                  {newSite.description && <p className="text-mist">{newSite.description}</p>}
                  <p className="text-mist">
                    {newSite.lat.toFixed(6)}, {newSite.lng.toFixed(6)}
                  </p>
                  <Button type="button" variant="outline" className="mt-2" onClick={() => setSiteDialog(true)}>
                    Ubah lokasi baru
                  </Button>
                </div>
              )}
            </Section>

            <Section title="Detail pekerjaan per hari">
              <div className="grid gap-x-3 md:grid-cols-2">
                <TextField label="Tanggal mulai" type="date" readOnly={revise && detail?.plan.status === "IN_PROGRESS"} error={errors.period_start?.message} {...register("period_start")} />
                {!oneDay && <TextField label="Tanggal selesai" type="date" error={errors.period_end?.message} {...register("period_end")} />}
              </div>
              <label className="mb-2 flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="size-5" {...register("one_day")} />
                Rencana kerja 1 hari
              </label>
              <label className="mb-2 flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="size-5" {...register("is_out_of_town")} />
                Luar kota (uang absen luar kota)
              </label>
              {days.fields.length === 0 ? (
                <p className="text-sm text-mist">Pilih rentang tanggal; daftar hari kerja akan muncul untuk diisi.</p>
              ) : (
                <ol className="space-y-4">
                  {days.fields.map((day, i) => (
                    <DayCard
                      key={day.id}
                      index={i}
                      workDate={day.work_date}
                      control={control}
                      register={register}
                      setValue={setValue}
                      errors={errors}
                      sites={o.sites}
                      team={members.map((m) => ({ id: m, name: people.get(m) ?? m }))}
                      canHoliday={i > 0 && i < days.fields.length - 1}
                      onHoliday={() => markHoliday(day.work_date)}
                    />
                  ))}
                </ol>
              )}
              {days.fields.length > 1 && (
                <Button type="button" variant="outline" className="mt-3 w-full" onClick={copyFirstToAll}>
                  Samakan judul &amp; deskripsi semua hari dengan hari pertama
                </Button>
              )}
              {holidays.length > 0 && (
                <div className="mt-3 rounded-control border border-line p-3" aria-label="Hari libur">
                  <p className="mb-2 text-sm font-medium">Hari libur ({holidays.length})</p>
                  <ul className="space-y-1">
                    {holidays.map((h) => (
                      <li key={h} className="flex items-center justify-between gap-2 text-sm">
                        <span>{formatDate(h)}</span>
                        <Button type="button" variant="outline" size="sm" onClick={() => revokeHoliday(h)}>
                          Jadikan hari kerja
                        </Button>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-mist">Hari libur tidak wajib absen dan laporan. Hari yang sudah berlaporan tidak dapat diliburkan.</p>
                </div>
              )}
              {end && !oneDay && (
                <Button type="button" variant="outline" className="mt-3 w-full" onClick={() => setValue("period_end", nextDay(end))}>
                  <Plus className="size-4" /> Tambah hari kerja
                </Button>
              )}
            </Section>

            <Section title="Alat & kendaraan">
              <fieldset className="mb-4">
                <legend className="mb-2 text-sm font-medium">Alat</legend>
                {o.tools.length === 0 ? (
                  <p className="text-sm text-mist">Tidak ada alat yang siap pakai.</p>
                ) : (
                  <div className="max-h-48 space-y-1 overflow-y-auto rounded-control border border-line p-2">
                    {o.tools.map((t) => (
                      <label key={t.id} className="flex min-h-11 items-center gap-2 text-sm">
                        <input type="checkbox" className="size-5" value={t.id} {...register("tool_ids")} />
                        {t.name} · {t.code}
                      </label>
                    ))}
                  </div>
                )}
                <p className="mt-1 text-sm text-mist">Hanya alat siap pakai yang tidak terikat work plan lain dan tidak dipinjam.</p>
              </fieldset>
              <SelectField
                label="Kendaraan (opsional)"
                hint="Hanya kendaraan siap pakai yang tidak terikat work plan lain dan tidak dipinjam."
                {...register("vehicle_id")}
              >
                <option value="">Tanpa kendaraan</option>
                {o.vehicles.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} · {v.code} ({v.vehicle_type === "MOTORCYCLE" ? "roda dua, SIM C" : "SIM A"})
                  </option>
                ))}
              </SelectField>
            </Section>

            <Section title="Tim">
              <SelectField
                label="Ketua tim"
                error={errors.leader_employee_id?.message}
                hint="Bukan akun kantor dan tidak terikat work plan yang berjalan atau terjadwal."
                {...register("leader_employee_id")}
              >
                <option value="">Pilih ketua tim</option>
                {o.leaders.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name} — {p.position}
                  </option>
                ))}
              </SelectField>
              <fieldset className="mb-4">
                <legend className="mb-2 text-sm font-medium">Anggota tim</legend>
                <div className="max-h-56 space-y-1 overflow-y-auto rounded-control border border-line p-2">
                  {o.members.filter((p) => String(p.id) !== leader).length === 0 && (
                    <p className="p-2 text-sm text-mist">Tidak ada bawahan yang bebas tugas.</p>
                  )}
                  {o.members
                    .filter((p) => String(p.id) !== leader)
                    .map((p) => (
                      <label key={p.id} className="flex min-h-11 items-center gap-2 text-sm">
                        <input type="checkbox" className="size-5" value={p.id} {...register("member_employee_ids")} />
                        <span>
                          {p.full_name} <span className="text-mist">— {p.position}</span>
                        </span>
                      </label>
                    ))}
                </div>
                <p className="mt-1 text-sm text-mist">Bawahan Anda yang bukan akun kantor dan tidak terikat work plan lain.</p>
                {errors.member_employee_ids && <p className="mt-1 text-sm text-destructive">{errors.member_employee_ids.message}</p>}
              </fieldset>
              {vehicle && (
                <SelectField
                  label="Driver"
                  error={errors.driver_employee_id?.message}
                  hint={
                    candidates.length === 0
                      ? "Pilih ketua/anggota dulu."
                      : drivers.data && drivers.data.length === 0
                        ? "Tidak ada ketua/anggota dengan SIM yang sesuai tipe kendaraan."
                        : "Ketua atau anggota terpilih dengan SIM sesuai tipe kendaraan."
                  }
                  {...register("driver_employee_id")}
                >
                  <option value="">{drivers.isFetching ? "Memuat..." : "Pilih driver"}</option>
                  {drivers.data?.map((d) => (
                    <option key={d} value={d}>
                      {people.get(d) ?? d}
                    </option>
                  ))}
                </SelectField>
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

function DayCard({
  index,
  workDate,
  control,
  register,
  setValue,
  errors,
  sites,
  team,
  canHoliday,
  onHoliday,
}: {
  index: number;
  workDate: string;
  control: Control<Values>;
  register: UseFormRegister<Values>;
  setValue: UseFormSetValue<Values>;
  errors: FieldErrors<Values>;
  sites: { id: string; name: string }[];
  team: { id: string; name: string }[];
  canHoliday: boolean;
  onHoliday: () => void;
}) {
  const tasks = useFieldArray({ control, name: `days.${index}.tasks` });
  const memberMode = useWatch({ control, name: `days.${index}.member_mode` });
  const memberIds = useWatch({ control, name: `days.${index}.member_ids` });
  const live = useWatch({ control, name: `days.${index}.tasks` });
  const [uploading, setUploading] = useState<number | null>(null);
  const dayErr = errors.days?.[index];
  const filesOf = (t: number): TaskValue["files"] => live?.[t]?.files ?? [];

  const attach = async (t: number, list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (!files.length) return;
    const tooBig = oversize(files);
    if (tooBig) return toast.error(tooBig);
    setUploading(t);
    try {
      const ids = await uploadFiles(files);
      setValue(`days.${index}.tasks.${t}.files`, [...filesOf(t), ...ids.map((id, i) => ({ file_id: id, file_name: files[i].name }))]);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setUploading(null);
    }
  };

  return (
    <li className="rounded-control border border-line p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold">
          Hari {index + 1} · {formatDate(workDate)}
        </p>
        <Button type="button" variant="outline" size="sm" disabled={!canHoliday} onClick={onHoliday} title={canHoliday ? undefined : "Hari pertama dan terakhir tidak bisa diliburkan; ubah tanggal mulai/selesai."}>
          Tandai libur
        </Button>
      </div>
      <details className="mb-3 rounded-control border border-line p-3">
        <summary className="min-h-11 cursor-pointer text-sm font-medium">Lokasi &amp; anggota hari ini</summary>
        <SelectField label="Lokasi hari ini" hint="Absensi hari ini mengikuti lokasi ini." {...register(`days.${index}.site_id`)}>
          <option value="">Ikut lokasi rencana</option>
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </SelectField>
        <fieldset>
          <legend className="mb-1 text-sm font-medium">Anggota yang bertugas</legend>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="radio" className="size-5" value="all" {...register(`days.${index}.member_mode`)} /> Seluruh tim
          </label>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="radio" className="size-5" value="custom" {...register(`days.${index}.member_mode`)} /> Hanya yang dipilih (ketua selalu ikut)
          </label>
          {memberMode === "custom" && (
            <div className="ml-2 space-y-1">
              {team.length === 0 && <p className="text-sm text-mist">Belum ada anggota tim.</p>}
              {team.map((m) => (
                <label key={m.id} className="flex min-h-11 items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="size-5"
                    checked={memberIds.includes(m.id)}
                    onChange={(e) =>
                      setValue(`days.${index}.member_ids`, e.target.checked ? [...memberIds, m.id] : memberIds.filter((x) => x !== m.id), { shouldDirty: true })
                    }
                  />
                  {m.name}
                </label>
              ))}
            </div>
          )}
          <p className="mt-1 text-xs text-mist">Anggota yang tidak bertugas hari ini tetap tercatat di rencana, tetapi tidak wajib absen dan lapor.</p>
        </fieldset>
      </details>
      <div className="space-y-3">
        {tasks.fields.map((task, t) => (
          <div key={task.id} className="rounded-control bg-canvas p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">Detail pekerjaan {t + 1}</span>
              {tasks.fields.length > 1 && (
                <Button type="button" variant="ghost" size="sm" onClick={() => tasks.remove(t)} aria-label={`Hapus detail pekerjaan ${t + 1}`}>
                  <Trash2 className="size-4" />
                </Button>
              )}
            </div>
            <TextField
              label="Judul pekerjaan"
              placeholder="mis. Pemasangan CCTV 1"
              error={dayErr?.tasks?.[t]?.title?.message}
              {...register(`days.${index}.tasks.${t}.title`)}
            />
            <TextAreaField
              label="Deskripsi"
              placeholder="mis. Memasang CCTV 1 di area A"
              error={dayErr?.tasks?.[t]?.description?.message}
              {...register(`days.${index}.tasks.${t}.description`)}
            />
            <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-lens">
              <Paperclip className="size-4" />
              {uploading === t ? "Mengunggah..." : "Tambah foto atau PDF (opsional)"}
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                multiple
                className="sr-only"
                onChange={(e) => {
                  void attach(t, e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
            {filesOf(t).length > 0 && (
              <ul className="mt-1 space-y-1 text-sm">
                {filesOf(t).map((f) => (
                  <li key={f.file_id} className="flex items-center justify-between gap-2">
                    <span className="truncate">{f.file_name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setValue(`days.${index}.tasks.${t}.files`, filesOf(t).filter((x) => x.file_id !== f.file_id))}
                    >
                      Hapus
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {dayErr?.tasks?.message && <p className="mt-1 text-sm text-destructive">{dayErr.tasks.message}</p>}
      <Button type="button" variant="outline" className="mt-3 w-full" onClick={() => tasks.append(emptyTask())}>
        <Plus className="size-4" /> Tambah detail pekerjaan
      </Button>
    </li>
  );
}
