import { useState } from "react";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { InlineLink } from "@/components/molecules/Links";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ApiError } from "@/lib/apiClient";
import {
  addDays,
  useDailyFormOptions,
  useCreatePlanItem,
  usePrerequisiteOptions,
  useDecideRollover,
  useDeletePlanItem,
  type DailyPlanDetail,
  type PlanItemCreate,
} from "@/services/dailyPlanService";
import { useWorkTypes } from "@/services/workTypeService";
import { PHASE_LABEL } from "@/lib/workPhase";
import { ItemEvidence } from "./ItemEvidence";

const PHASE: Record<string, string> = PHASE_LABEL;
const MAIN = ["INSTALLATION", "REPLACEMENT", "MAINTENANCE"];
const STATUS: Record<string, string> = {
  TODO: "Belum mulai", IN_PROGRESS: "Dikerjakan", DONE: "Selesai", PENDING_ROLLOVER: "Minta pindah hari", SHIFTED_DAY: "Pindah hari",
};
const message = (err: unknown) => (err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");

/** Item per titik pada jadwal harian: daftar, tambah (PM saat draf), hapus, dan keputusan geser (PM). */
export function DailyItemsPanel({ detail, loading, canPlan }: { detail: DailyPlanDetail | undefined; loading: boolean; canPlan: boolean }) {
  const editable = canPlan && !!detail && (detail.status === "DRAFT" || detail.status === "SUBMITTED");
  const remove = useDeletePlanItem();
  const decide = useDecideRollover();
  const [adding, setAdding] = useState(false);
  const [deciding, setDeciding] = useState<string | null>(null);
  const [shown, setShown] = useState<string | null>(null);

  return (
    <section aria-label="Daftar pekerjaan">
      <div className="mb-2 flex items-center justify-between">
        <TextBlock as="h3" className="font-semibold">Daftar pekerjaan</TextBlock>
        {editable && !adding && <ActionButton size="sm" variant="outline" onClick={() => setAdding(true)}>Tambah pekerjaan</ActionButton>}
      </div>
      {loading && <LoadingBar className="h-4 w-1/2" />}
      {detail?.items.length === 0 && !adding && (
        <TextBlock className="text-mist">Belum ada pekerjaan. Satu lokasi titik = satu pekerjaan (survei, persiapan, instalasi, replacement, maintenance).</TextBlock>
      )}
      <ListBlock className="divide-y divide-line">
        {/* Titik survei tampil di halaman Survei (dikelompokkan per tugas survei), bukan sebagai item terpisah. */}
        {detail?.items.filter((i) => !(i.task_phase === "SURVEY" && i.depends_on_item_id)).map((i) => (
          <ListEntry key={i.item_id} className="space-y-2 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <TextBlock as="span">
                {PHASE[i.task_phase] ?? i.task_phase} · {i.title}
                {i.location_name && !i.title.includes(i.location_name) ? ` · ${i.location_name}` : ""}
              </TextBlock>
              <div className="flex items-center gap-2">
                <Pill tone={i.status === "DONE" ? "success" : i.status === "PENDING_ROLLOVER" ? "warning" : "neutral"}>
                  {`${STATUS[i.status] ?? i.status} · ${Number(i.completed_qty)}/${Number(i.target_qty)}`}
                </Pill>
                {i.task_phase === "SURVEY" && i.completion_id && (
                  <InlineLink to={`/surveys/${i.item_id}`} className="text-sm text-lens underline">Buka survei</InlineLink>
                )}
                <ActionButton size="sm" variant="outline" onClick={() => setShown(shown === i.item_id ? null : i.item_id)}>
                  {shown === i.item_id ? "Tutup bukti" : "Lihat bukti"}
                </ActionButton>
                {canPlan && i.rollover_approval_status === "WAITING_PM" && (
                  <ActionButton size="sm" onClick={() => setDeciding(i.item_id)}>Putuskan pindah hari</ActionButton>
                )}
                {editable && (
                  <ActionButton
                    size="sm"
                    variant="ghost"
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(i.item_id, { onSuccess: () => toast.success("Item dihapus."), onError: (e) => toast.error(message(e)) })}
                  >
                    Hapus
                  </ActionButton>
                )}
              </div>
            </div>
            {shown === i.item_id && <ItemEvidence itemId={i.item_id} />}
            {deciding === i.item_id && detail && (
              <FormBlock
                className="space-y-2 rounded-control border border-line p-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  const target_date = String(new FormData(e.currentTarget).get("target_date") ?? "");
                  const note = String(new FormData(e.currentTarget).get("note") ?? "").trim() || null;
                  decide.mutate(
                    { itemId: i.item_id, approve: true, target_date, note },
                    { onSuccess: () => { toast.success("Pekerjaan dipindah; sisanya lanjut di hari baru."); setDeciding(null); }, onError: (err) => toast.error(message(err)) },
                  );
                }}
              >
                <TextBlock className="text-mist">Alasan ketua: {i.delay_reason ?? "-"}</TextBlock>
                <TextField name="target_date" label="Pindah ke tanggal" type="date" defaultValue={addDays(detail.work_date, 1)} />
                <TextAreaField name="note" label="Catatan PM (opsional)" />
                <div className="flex gap-2">
                  <ActionButton type="submit" size="sm" disabled={decide.isPending}>Setujui pindah hari</ActionButton>
                  <ActionButton
                    size="sm"
                    variant="outline"
                    disabled={decide.isPending}
                    onClick={() =>
                      decide.mutate(
                        { itemId: i.item_id, approve: false },
                        { onSuccess: () => { toast.success("Permintaan pindah hari ditolak."); setDeciding(null); }, onError: (err) => toast.error(message(err)) },
                      )
                    }
                  >
                    Tolak
                  </ActionButton>
                </div>
              </FormBlock>
            )}
          </ListEntry>
        ))}
      </ListBlock>
      {adding && detail && <ItemForm detail={detail} onDone={() => setAdding(false)} />}
    </section>
  );
}

function ItemForm({ detail, onDone }: { detail: DailyPlanDetail; onDone: () => void }) {
  // Jenis titik survei hanya dipakai di dalam survei, bukan sebagai item jadwal.
  const types = useWorkTypes(false, detail.division_id).data?.filter((w) => w.kind !== "SURVEY_POINT");
  const formOptions = useDailyFormOptions(true).data;
  const orders = (formOptions?.orders ?? []).filter(
    (o) => !o.division_id || o.division_id === detail.division_id
  );
  const create = useCreatePlanItem(detail.daily_plan_id);
  const prereqs = usePrerequisiteOptions(detail.daily_plan_id).data ?? [];
  const [phase, setPhase] = useState("SURVEY");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const v = (k: string) => String(f.get(k) ?? "").trim();
    setError(null);
    const latVal = v("site_lat");
    const lngVal = v("site_lng");
    const startTimeVal = v("start_time");
    const endTimeVal = v("end_time");

    const body: PlanItemCreate = {
      work_type_id: v("work_type_id"),
      title: v("title"),
      task_phase: phase as PlanItemCreate["task_phase"],
      is_main_deliverable: MAIN.includes(phase) && v("main") === "yes",
      completion_id: v("completion_id") || undefined,
      target_qty: v("target_qty") || "1",
      location_name: v("location_name") || null,
      start_time: startTimeVal || null,
      end_time: endTimeVal || null,
      site_lat: latVal ? Number(latVal) : null,
      site_lng: lngVal ? Number(lngVal) : null,
      depends_on_item_id: v("depends_on_item_id") || null,
      notes: v("notes") || null,
    };
    if (!body.work_type_id) return setError("Pilih template (jenis pekerjaan) divisi ini.");
    if (body.title.length < 3) return setError("Nama pekerjaan minimal 3 huruf.");
    if (Number(body.target_qty) <= 0 || isNaN(Number(body.target_qty))) {
      return setError("Target volume harus lebih dari 0.");
    }
    if ((latVal && !lngVal) || (!latVal && lngVal)) {
      return setError("Lintang dan bujur lokasi harus diisi berpasangan.");
    }
    if (startTimeVal && endTimeVal && endTimeVal <= startTimeVal) {
      return setError("Jam selesai item harus setelah jam mulai.");
    }
    create.mutate(body, { onSuccess: () => { toast.success("Item ditambahkan."); onDone(); }, onError: (err) => setError(message(err)) });
  };

  return (
    <FormBlock className="mt-3 space-y-1 rounded-control border border-line p-3" onSubmit={submit} noValidate>
      {error && <TextBlock role="alert" className="text-danger">{error}</TextBlock>}
      {orders.length > 0 && (
        <SelectField name="completion_id" label="Pekerjaan Klien / Order SPK (opsional)" defaultValue="">
          <ControlOption value="">Bukan bagian order tertentu</ControlOption>
          {orders.map((o) => (
            <ControlOption key={o.completion_id} value={o.completion_id}>
              {o.order_number ? `[${o.order_number}] ` : ""}{o.client_name} - {o.project_title}
            </ControlOption>
          ))}
        </SelectField>
      )}
      <SelectField name="work_type_id" label="Template (jenis pekerjaan divisi)" defaultValue="">
        <ControlOption value="">Pilih template</ControlOption>
        {types?.map((t) => <ControlOption key={t.id} value={t.id}>{t.name}</ControlOption>)}
      </SelectField>
      <TextField name="title" label="Judul titik" hint="Contoh: Titik CCTV 03 — Pos Jaga Utara" />
      <div className="grid gap-x-3 md:grid-cols-2">
        <SelectField label="Fase" value={phase} onChange={(e) => setPhase(e.target.value)}>
          {Object.entries(PHASE).map(([k, l]) => <ControlOption key={k} value={k}>{l}</ControlOption>)}
        </SelectField>
        {MAIN.includes(phase) && (
          <SelectField name="main" label="Hasil utama pekerjaan klien?" defaultValue="yes">
            <ControlOption value="yes">Ya</ControlOption>
            <ControlOption value="no">Tidak</ControlOption>
          </SelectField>
        )}
      </div>
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField name="target_qty" label="Target volume" inputMode="decimal" defaultValue="1" />
        <TextField name="location_name" label="Nama titik/lokasi (opsional)" />
      </div>
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField name="start_time" label="Jam mulai (opsional)" type="time" />
        <TextField name="end_time" label="Jam selesai (opsional)" type="time" />
      </div>
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField name="site_lat" label="Latitude titik (opsional)" inputMode="decimal" placeholder="misal: -6.2088" />
        <TextField name="site_lng" label="Longitude titik (opsional)" inputMode="decimal" placeholder="misal: 106.8456" />
      </div>
      {prereqs.length > 0 && (
        <SelectField
          name="depends_on_item_id"
          label="Harus selesai dulu (opsional)"
          hint="Pekerjaan ini baru bisa dikerjakan setelah pekerjaan yang dipilih selesai — boleh pekerjaan tim lain di lokasi yang sama."
          defaultValue=""
        >
          <ControlOption value="">Tidak ada</ControlOption>
          {prereqs.map((i) => (
            <ControlOption key={i.item_id} value={i.item_id}>
              {`${formatDate(i.work_date)} · ${PHASE[i.task_phase as keyof typeof PHASE] ?? i.task_phase} · ${i.title}${i.other_team ? ` (${i.team_name})` : ""}`}
            </ControlOption>
          ))}
        </SelectField>
      )}
      <TextAreaField name="notes" label="Remark (hasil survei, kebutuhan alat)" />
      <div className="flex gap-2">
        <ActionButton type="submit" size="sm" disabled={create.isPending}>Simpan pekerjaan</ActionButton>
        <ActionButton size="sm" variant="ghost" onClick={onDone}>Batal</ActionButton>
      </div>
    </FormBlock>
  );
}
