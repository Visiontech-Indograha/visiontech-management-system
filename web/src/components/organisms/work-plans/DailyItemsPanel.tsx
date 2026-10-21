import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ApiError } from "@/lib/apiClient";
import {
  addDays,
  useCreatePlanItem,
  useDecideRollover,
  useDeletePlanItem,
  type DailyPlanDetail,
  type PlanItemCreate,
} from "@/services/dailyPlanService";
import { useWorkTypes } from "@/services/workTypeService";

const PHASE: Record<string, string> = {
  SURVEY: "Survei", PREPARATION: "Persiapan", INSTALLATION: "Instalasi", REPLACEMENT: "Penggantian", MAINTENANCE: "Pemeliharaan",
};
const MAIN = ["INSTALLATION", "REPLACEMENT", "MAINTENANCE"];
const STATUS: Record<string, string> = {
  TODO: "Belum mulai", IN_PROGRESS: "Dikerjakan", DONE: "Selesai", PENDING_ROLLOVER: "Minta digeser", SHIFTED_DAY: "Digeser",
};
const message = (err: unknown) => (err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");

/** Item per titik pada jadwal harian: daftar, tambah (PM saat draf), hapus, dan keputusan geser (PM). */
export function DailyItemsPanel({ detail, loading, canPlan }: { detail: DailyPlanDetail | undefined; loading: boolean; canPlan: boolean }) {
  const editable = canPlan && !!detail && (detail.status === "DRAFT" || detail.status === "SUBMITTED");
  const remove = useDeletePlanItem();
  const decide = useDecideRollover();
  const [adding, setAdding] = useState(false);
  const [deciding, setDeciding] = useState<string | null>(null);

  return (
    <section aria-label="Item pekerjaan">
      <div className="mb-2 flex items-center justify-between">
        <TextBlock as="h3" className="font-semibold">Item pekerjaan</TextBlock>
        {editable && !adding && <ActionButton size="sm" variant="outline" onClick={() => setAdding(true)}>Tambah item</ActionButton>}
      </div>
      {loading && <LoadingBar className="h-4 w-1/2" />}
      {detail?.items.length === 0 && !adding && (
        <TextBlock className="text-mist">Belum ada item. Satu titik = satu item (survei, persiapan, instalasi/penggantian/pemeliharaan).</TextBlock>
      )}
      <ListBlock className="divide-y divide-line">
        {detail?.items.map((i) => (
          <ListEntry key={i.item_id} className="space-y-2 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <TextBlock as="span">
                {PHASE[i.task_phase] ?? i.task_phase} · {i.title}
                {i.location_name ? ` · ${i.location_name}` : ""}
              </TextBlock>
              <div className="flex items-center gap-2">
                <Pill tone={i.status === "DONE" ? "success" : i.status === "PENDING_ROLLOVER" ? "warning" : "neutral"}>
                  {`${STATUS[i.status] ?? i.status} · ${Number(i.completed_qty)}/${Number(i.target_qty)}`}
                </Pill>
                {canPlan && i.rollover_approval_status === "WAITING_PM" && (
                  <ActionButton size="sm" onClick={() => setDeciding(i.item_id)}>Putuskan geser</ActionButton>
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
            {deciding === i.item_id && detail && (
              <FormBlock
                className="space-y-2 rounded-control border border-line p-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  const target_date = String(new FormData(e.currentTarget).get("target_date") ?? "");
                  const note = String(new FormData(e.currentTarget).get("note") ?? "").trim() || null;
                  decide.mutate(
                    { itemId: i.item_id, approve: true, target_date, note },
                    { onSuccess: () => { toast.success("Item digeser; sisa volume terbawa."); setDeciding(null); }, onError: (err) => toast.error(message(err)) },
                  );
                }}
              >
                <TextBlock className="text-mist">Alasan ketua: {i.delay_reason ?? "-"}</TextBlock>
                <TextField name="target_date" label="Geser ke tanggal" type="date" defaultValue={addDays(detail.work_date, 1)} />
                <TextAreaField name="note" label="Catatan PM (opsional)" />
                <div className="flex gap-2">
                  <ActionButton type="submit" size="sm" disabled={decide.isPending}>Setujui geser</ActionButton>
                  <ActionButton
                    size="sm"
                    variant="outline"
                    disabled={decide.isPending}
                    onClick={() =>
                      decide.mutate(
                        { itemId: i.item_id, approve: false },
                        { onSuccess: () => { toast.success("Permintaan geser ditolak."); setDeciding(null); }, onError: (err) => toast.error(message(err)) },
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
  const types = useWorkTypes(false, detail.division_id);
  const create = useCreatePlanItem(detail.daily_plan_id);
  const [phase, setPhase] = useState("SURVEY");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const v = (k: string) => String(f.get(k) ?? "").trim();
    setError(null);
    const body: PlanItemCreate = {
      work_type_id: v("work_type_id"),
      title: v("title"),
      task_phase: phase as PlanItemCreate["task_phase"],
      is_main_deliverable: MAIN.includes(phase) && v("main") === "yes",
      target_qty: v("target_qty") || "1",
      location_name: v("location_name") || null,
      depends_on_item_id: v("depends_on_item_id") || null,
      notes: v("notes") || null,
    };
    if (!body.work_type_id) return setError("Pilih template (jenis pekerjaan) divisi ini.");
    if (body.title.length < 3) return setError("Judul item minimal 3 huruf.");
    create.mutate(body, { onSuccess: () => { toast.success("Item ditambahkan."); onDone(); }, onError: (err) => setError(message(err)) });
  };

  return (
    <FormBlock className="mt-3 space-y-1 rounded-control border border-line p-3" onSubmit={submit} noValidate>
      {error && <TextBlock role="alert" className="text-danger">{error}</TextBlock>}
      <SelectField name="work_type_id" label="Template (jenis pekerjaan divisi)" defaultValue="">
        <ControlOption value="">Pilih template</ControlOption>
        {types.data?.map((t) => <ControlOption key={t.id} value={t.id}>{t.name}</ControlOption>)}
      </SelectField>
      <TextField name="title" label="Judul titik" hint="Contoh: Titik CCTV 03 — Pos Jaga Utara" />
      <div className="grid gap-x-3 md:grid-cols-2">
        <SelectField label="Fase" value={phase} onChange={(e) => setPhase(e.target.value)}>
          {Object.entries(PHASE).map(([k, l]) => <ControlOption key={k} value={k}>{l}</ControlOption>)}
        </SelectField>
        {MAIN.includes(phase) && (
          <SelectField name="main" label="Deliverable utama order?" defaultValue="yes">
            <ControlOption value="yes">Ya</ControlOption>
            <ControlOption value="no">Tidak</ControlOption>
          </SelectField>
        )}
      </div>
      <div className="grid gap-x-3 md:grid-cols-2">
        <TextField name="target_qty" label="Target volume" inputMode="decimal" defaultValue="1" />
        <TextField name="location_name" label="Nama titik/lokasi (opsional)" />
      </div>
      {detail.items.length > 0 && (
        <SelectField name="depends_on_item_id" label="Prasyarat (opsional)" defaultValue="">
          <ControlOption value="">Tanpa prasyarat</ControlOption>
          {detail.items.map((i) => <ControlOption key={i.item_id} value={i.item_id}>{PHASE[i.task_phase]} · {i.title}</ControlOption>)}
        </SelectField>
      )}
      <TextAreaField name="notes" label="Remark (hasil survei, kebutuhan alat)" />
      <div className="flex gap-2">
        <ActionButton type="submit" size="sm" disabled={create.isPending}>Simpan item</ActionButton>
        <ActionButton size="sm" variant="ghost" onClick={onDone}>Batal</ActionButton>
      </div>
    </FormBlock>
  );
}
