import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ControlLabel, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  cellResultText,
  datesBetween,
  itemPayload,
  longDate,
  MAX_TEAMS,
  summarizeBulk,
  validateRange,
  type BulkCell,
  type WeeklyRow,
} from "@/lib/alokasi";
import { errorMessage } from "@/lib/errors";
import type { DailyFormOptions } from "@/services/dailyPlanService";
import { useIdempotencyKey } from "@/lib/idempotency";
import { addItemToPlan, useBulkAllocate, useOrderSchedule } from "@/services/alokasiService";
import { useWorkTypes } from "@/services/workTypeService";

export interface AllocCell {
  team_id: string;
  work_date: string;
}

interface ResultRow {
  cell: BulkCell;
  teamName: string;
  itemError: string | null;
}

/** Dialog "Alokasikan": order, tim, rentang hari kerja, template pekerjaan, target per hari → POST bulk → hasil per sel. */
export function AllocateDialog({ divisionId, cells, teams, orders, today, onClose }: {
  divisionId: string;
  cells: AllocCell[];
  teams: WeeklyRow[];
  orders: DailyFormOptions["orders"];
  today: string;
  onClose: () => void;
}) {
  const initialTeams = [...new Set(cells.map((c) => c.team_id))];
  const initialDates = cells.map((c) => c.work_date).sort();
  const [teamIds, setTeamIds] = useState<string[]>(initialTeams);
  const [start, setStart] = useState(initialDates[0] ?? today);
  const [end, setEnd] = useState(initialDates[initialDates.length - 1] ?? today);
  const [skipWeekend, setSkipWeekend] = useState(false);
  const [completionId, setCompletionId] = useState("");
  const [workTypeId, setWorkTypeId] = useState("");
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("1");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ created: number; skipped: number; warnings: number; rows: ResultRow[] } | null>(null);
  const [busy, setBusy] = useState(false);

  const dirty = !result && (
    teamIds.length !== initialTeams.length || completionId !== "" || workTypeId !== "" || title !== "" ||
    location !== "" || target !== "1" || skipWeekend
  );

  const bulk = useBulkAllocate();
  const idem = useIdempotencyKey(JSON.stringify([divisionId, teamIds, start, end, skipWeekend]));
  const schedule = useOrderSchedule(completionId);
  const types = useWorkTypes(false, divisionId).data?.filter((w) => w.kind !== "SURVEY_POINT") ?? [];
  const orderOptions = orders.filter((o) => !o.division_id || o.division_id === divisionId);
  const rangeError = validateRange(start, end);
  const dates = rangeError ? [] : datesBetween(start, end, skipWeekend);
  const targetNum = Number(target.replace(",", "."));
  const planned = teamIds.length * dates.length;
  const teamName = (id: string) => teams.find((t) => t.team_id === id)?.team_name ?? "Tim";

  const toggleTeam = (id: string, on: boolean) =>
    setTeamIds((prev) => (on ? [...prev, id] : prev.filter((x) => x !== id)));

  const submit = async () => {
    if (rangeError) return setError(rangeError);
    if (!dates.length) return setError("Tidak ada hari kerja pada rentang ini.");
    if (!teamIds.length) return setError("Pilih minimal satu tim.");
    if (teamIds.length > MAX_TEAMS) return setError(`Maksimal ${MAX_TEAMS} tim per permintaan.`);
    if (!completionId) return setError("Pilih order klien.");
    if (!workTypeId) return setError("Pilih jenis pekerjaan (template).");
    if (title.trim().length < 3) return setError("Judul pekerjaan minimal 3 karakter.");
    if (!(targetNum > 0)) return setError("Target per hari harus lebih dari 0.");
    setError(null);
    setBusy(true);
    try {
      const out = await bulk.mutateAsync({ division_id: divisionId, team_ids: teamIds, work_dates: dates, idempotencyKey: idem.key });
      idem.renew();
      const rows: ResultRow[] = [];
      for (const cell of out.cells) {
        let itemError: string | null = null;
        if (cell.status === "CREATED" && cell.daily_plan_id) {
          try {
            await addItemToPlan(cell.daily_plan_id, itemPayload({ workTypeId, title, completionId, target: targetNum, location }));
          } catch (err) {
            itemError = errorMessage(err, "Pekerjaan belum ditambahkan ke jadwal ini.");
          }
        }
        rows.push({ cell, teamName: teamName(cell.team_id), itemError });
      }
      const summary = summarizeBulk(out);
      setResult({ ...summary, rows });
      toast.success(`${summary.created} jadwal dibuat${summary.skipped ? `, ${summary.skipped} dilewati` : ""}.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const s = schedule.data;

  return (
    <VmsDialog
      open
      title="Alokasikan"
      onClose={onClose}
      dirty={dirty}
      footer={result ? (
        <ActionButton onClick={onClose}>Tutup</ActionButton>
      ) : (
        <DialogActions onCancel={onClose} busy={busy} formId="alokasi-form" submitLabel="Alokasikan"
                       busyLabel="Mengalokasikan..." />
      )}
    >
      {result ? (
        <div className="space-y-3">
          <TextBlock className="font-medium">Hasil alokasi</TextBlock>
          <TextBlock>
            {result.created} jadwal dibuat, {result.skipped} dilewati
            {result.warnings ? `, ${result.warnings} peringatan` : ""}. Jadwal dibuat sebagai draf; setujui dari Jadwal harian.
          </TextBlock>
          <ListBlock aria-label="Hasil per sel" className="space-y-1 text-sm">
            {result.rows.map((r) => (
              <ListEntry key={`${r.cell.team_id}|${r.cell.work_date}`} className="rounded-md border p-2">
                <TextBlock as="span" className="font-medium">{r.teamName}, {longDate(r.cell.work_date)}:</TextBlock>{" "}
                {cellResultText(r.cell)}
                {(r.cell.warnings ?? []).map((w) => (
                  <TextBlock as="span" key={w.code} className="block text-warning">
                    Peringatan {w.code === "LEADER_CUTI" ? "cuti ketua" : "aset bentrok"}: {w.message}
                  </TextBlock>
                ))}
                {r.itemError && (
                  <TextBlock as="span" className="block text-danger">Pekerjaan gagal ditambahkan: {r.itemError}</TextBlock>
                )}
              </ListEntry>
            ))}
          </ListBlock>
        </div>
      ) : (
        <FormBlock id="alokasi-form" className="space-y-4" noValidate
                   onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <SelectField label="Order klien" value={completionId} onChange={(e) => setCompletionId(e.target.value)}>
            <ControlOption value="">Pilih order</ControlOption>
            {orderOptions.map((o) => (
              <ControlOption key={o.completion_id} value={o.completion_id}>
                {o.client_name} — {o.project_title}{o.order_number ? ` (${o.order_number})` : ""}
              </ControlOption>
            ))}
          </SelectField>
          {orderOptions.length === 0 && (
            <TextBlock className="text-sm text-mist">
              Belum ada order klien untuk divisi ini. Order muncul setelah survei work order selesai dan disetujui PM.
              Tugaskan survei dulu dari halaman work order.
            </TextBlock>
          )}
          {completionId && (
            <div role="status" className="rounded-md bg-hover p-2 text-sm">
              {s ? (
                <>
                  <TextBlock>
                    Sisa belum dijadwalkan: {s.unscheduled_target_qty} dari total {s.total_target_unit} (selesai {s.completed_target_unit}).
                  </TextBlock>
                  {planned > s.unscheduled_target_qty && (
                    <TextBlock className="text-warning">
                      Rencana {planned} jadwal melebihi sisa target; tetap bisa disimpan.
                    </TextBlock>
                  )}
                </>
              ) : (
                <TextBlock>Memuat sisa target order...</TextBlock>
              )}
            </div>
          )}

          <div className="space-y-2">
            <TextBlock className="mb-1 text-sm font-medium">Tim</TextBlock>
            {teams.map((t) => {
              const id = `alokasi-tim-${t.team_id}`;
              return (
                <div key={t.team_id} className="flex items-center gap-2">
                  <CheckControl id={id} checked={teamIds.includes(t.team_id)}
                                onCheckedChange={(v) => toggleTeam(t.team_id, v === true)} />
                  <ControlLabel htmlFor={id}>{t.team_name}</ControlLabel>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <TextField label="Mulai" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            <TextField label="Selesai" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <CheckControl id="alokasi-hari-kerja" checked={skipWeekend} onCheckedChange={(v) => setSkipWeekend(v === true)} />
            <ControlLabel htmlFor="alokasi-hari-kerja">Hanya hari kerja (Senin–Jumat)</ControlLabel>
          </div>
          <TextBlock className="text-sm">{dates.length} hari × {teamIds.length} tim = {planned} jadwal.</TextBlock>

          <SelectField label="Jenis pekerjaan (template)" value={workTypeId} onChange={(e) => setWorkTypeId(e.target.value)}>
            <ControlOption value="">Pilih template</ControlOption>
            {types.map((w) => <ControlOption key={w.id} value={w.id}>{w.name}</ControlOption>)}
          </SelectField>
          <TextField label="Judul pekerjaan" value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextField label="Target per hari" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} />
          <TextField label="Lokasi (opsional)" value={location} onChange={(e) => setLocation(e.target.value)}
                     hint="Lokasi default dari order belum tersedia di API; isi bila perlu." />
          <FormErrorText message={error} />
        </FormBlock>
      )}
    </VmsDialog>
  );
}
