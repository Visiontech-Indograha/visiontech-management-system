import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { displayPct, PHASE_COLOR, PHASE_LABEL, PHASES, phaseColor, phaseLabel, WORK_STATE, workState, type Phase } from "@/lib/workPhase";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { addDays, BACKDATE_DAYS, useDailyPlans, useDeleteDailyPlan, weekStart, type DailyPlan } from "@/services/dailyPlanService";

const MONTH = new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric", timeZone: "UTC" });
const LONG = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
const WEEKDAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const asDate = (d: string) => new Date(`${d}T00:00:00Z`);
const shiftMonth = (first: string, delta: number) => {
  const d = asDate(first);
  d.setUTCMonth(d.getUTCMonth() + delta);
  return d.toISOString().slice(0, 10);
};
const mainPhase = (p: DailyPlan) => p.phases?.[0] ?? "PREPARATION";
/** Jadwal yang boleh dihapus massal: draf, diajukan, atau disetujui yang belum dimulai (API tetap menjadi penentu). */
const DELETABLE_STATUS = ["DRAFT", "SUBMITTED", "APPROVED"];

export interface MatrixTeam {
  team_id: string;
  name: string;
  division_id: string;
}

/**
 * Kalender bulanan jadwal tim. Tiap hari menampilkan jadwal berwarna per jenis pekerjaan
 * (Survei/Persiapan/Instalasi/Replacement/Maintenance); hari tanpa jadwal tampak jelas "Kosong".
 * Klik hari → kartu tim hari itu di bawah kalender.
 */
export function DailyWeekMatrix({ teams, start, today, divisionId, canPlan, onOpen, onCreate }: {
  teams: MatrixTeam[];
  start: string;
  today: string;
  divisionId?: string;
  canPlan: boolean;
  onOpen: (plan: DailyPlan) => void;
  onCreate: (team: MatrixTeam, workDate: string) => void;
}) {
  const [month, setMonth] = useState(() => `${start.slice(0, 7)}-01`);
  const [picked, setPicked] = useState(today);
  const [dayOpen, setDayOpen] = useState(false);
  const [only, setOnly] = useState<Phase | null>(null);
  const [sel, setSel] = useState<string[]>([]);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);
  const remove = useDeleteDailyPlan();
  const deletable = (p: DailyPlan) => canPlan && DELETABLE_STATUS.includes(p.status);

  /** Hapus berurutan; hasil dirangkum (berhasil & gagal beserta alasan pertama). */
  async function bulkDelete() {
    setBulkBusy(true);
    let ok = 0;
    const failures: string[] = [];
    for (const id of sel) {
      try {
        await remove.mutateAsync(id);
        ok += 1;
      } catch (err) {
        failures.push(err instanceof Error ? err.message : "galat");
      }
    }
    setBulkBusy(false);
    setBulkOpen(false);
    setSel([]);
    if (failures.length) toast.error(`${ok} jadwal dihapus, ${failures.length} gagal. ${failures[0]}`);
    else toast.success(`${ok} jadwal dihapus.`);
  }

  const gridStart = weekStart(month);
  const nextMonth = shiftMonth(month, 1);
  const weeks = Math.ceil((Math.round((asDate(nextMonth).getTime() - asDate(gridStart).getTime()) / 864e5)) / 7);
  const days = Array.from({ length: weeks * 7 }, (_, i) => addDays(gridStart, i));
  const plans = useDailyPlans({ start: days[0]!, end: days[days.length - 1]!, division_id: divisionId || undefined });

  const match = (p: DailyPlan) => !only || (p.phases ?? []).includes(only);
  const all = (plans.data ?? []).filter(match);
  const byDay = new Map<string, DailyPlan[]>();
  for (const p of all) byDay.set(p.work_date, [...(byDay.get(p.work_date) ?? []), p]);
  const rows = teams.length
    ? teams
    : [...new Map((plans.data ?? []).map((p) => [p.team_id, { team_id: p.team_id, name: p.team_name, division_id: p.division_id }])).values()];
  const dayPlans = byDay.get(picked) ?? [];
  const inMonth = (d: string) => d >= month && d < nextMonth;
  const emptyDays = days.filter((d) => inMonth(d) && !byDay.has(d)).length;

  return (
    <div className="space-y-4">
      {/* Bulan + keterangan warna (sekaligus saringan) */}
      <div className="flex flex-col gap-3 rounded-panel border border-line bg-surface p-3 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <ActionButton size="sm" variant="outline" aria-label="Bulan sebelumnya" onClick={() => setMonth(shiftMonth(month, -1))}>‹</ActionButton>
          <TextBlock as="h3" className="min-w-40 text-center text-base font-semibold capitalize">{MONTH.format(asDate(month))}</TextBlock>
          <ActionButton size="sm" variant="outline" aria-label="Bulan berikutnya" onClick={() => setMonth(shiftMonth(month, 1))}>›</ActionButton>
          <ActionButton size="sm" variant="ghost" onClick={() => { setMonth(`${today.slice(0, 7)}-01`); setPicked(today); }}>Bulan ini</ActionButton>
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Jenis pekerjaan">
          <ActionButton size="sm" className="rounded-full" variant={only === null ? "default" : "outline"} onClick={() => setOnly(null)}>Semua</ActionButton>
          {PHASES.map((ph) => (
            <ActionButton
              key={ph}
              size="sm"
              variant="outline"
              className={`rounded-full border ${PHASE_COLOR[ph].chip} ${only === ph ? "ring-2 ring-ink" : only ? "opacity-50" : ""}`}
              onClick={() => setOnly(only === ph ? null : ph)}
            >
              <TextBlock as="span" className={`mr-1.5 inline-block h-2.5 w-2.5 rounded-full ${PHASE_COLOR[ph].dot}`} />
              {PHASE_LABEL[ph]}
            </ActionButton>
          ))}
        </div>
      </div>

      <QueryState query={plans} errorText="Jadwal tidak dapat dimuat.">
        <TextBlock as="p" className="text-sm text-mist">
          {`${all.filter((p) => inMonth(p.work_date)).length} jadwal bulan ini · ${emptyDays} hari kosong`}
        </TextBlock>

        {/* Kalender */}
        <div className="overflow-hidden rounded-panel border border-line bg-surface shadow-card">
          <div className="grid grid-cols-7 border-b border-line bg-line/30">
            {WEEKDAYS.map((w) => (
              <TextBlock key={w} as="span" className="py-2 text-center text-xs font-semibold uppercase text-mist">{w}</TextBlock>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {days.map((d) => {
              const list = byDay.get(d) ?? [];
              const out = !inMonth(d);
              const active = d === picked;
              return (
                <ActionButton
                  key={d}
                  variant="ghost"
                  aria-label={`${LONG.format(asDate(d))}: ${list.length ? `${list.length} jadwal` : "kosong"}`}
                  onClick={() => {
                    setPicked(d);
                    // PM/OM: jendela hari selalu terbuka (baris tim tanpa jadwal → "Buat jadwal").
                    // Peran lain: satu jadwal → langsung detail; lebih dari satu → pilih dulu di jendela hari.
                    if (canPlan) setDayOpen(true);
                    else if (list.length === 1) onOpen(list[0]!);
                    else if (list.length > 1) setDayOpen(true);
                  }}
                  className={[
                    "flex h-auto min-h-20 flex-col items-stretch justify-start gap-1 rounded-none border-b border-r border-line p-1 text-left sm:min-h-28 sm:p-1.5",
                    out ? "opacity-40" : "",
                    !list.length && !out ? "bg-[repeating-linear-gradient(45deg,transparent,transparent_6px,rgba(127,127,127,0.07)_6px,rgba(127,127,127,0.07)_12px)]" : "",
                    active ? "ring-2 ring-inset ring-ink" : "",
                  ].join(" ")}
                >
                  <TextBlock
                    as="span"
                    className={`self-start rounded-full px-1.5 text-xs font-semibold ${d === today ? "bg-ink text-surface" : ""}`}
                  >
                    {Number(d.slice(8))}
                  </TextBlock>
                  {list.length === 0 ? (
                    !out && <TextBlock as="span" className="hidden text-[11px] text-mist sm:block">Kosong</TextBlock>
                  ) : (
                    <>
                      {/* Jenis pekerjaan langsung tertulis & berwarna; layar lebar ditambah nama tim. */}
                      <div className="flex flex-col gap-0.5">
                        {list.flatMap((p) => (p.phases?.length ? p.phases : ["PREPARATION"]).map((ph) => ({ p, ph }))).slice(0, 3).map(({ p, ph }) => (
                          <TextBlock
                            key={`${p.daily_plan_id}-${ph}`}
                            as="span"
                            title={`${phaseLabel(ph)} · ${p.team_name} · ${WORK_STATE[workState(p, today)].label}`}
                            className={`truncate rounded border px-1 py-0.5 text-[10px] font-semibold leading-tight sm:text-[11px] ${phaseColor(ph).chip}`}
                          >
                            <TextBlock as="span" className={`mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle ${WORK_STATE[workState(p, today)].dot}`} />
                            {phaseLabel(ph)}
                            <TextBlock as="span" className="hidden font-normal opacity-80 sm:inline">{` · ${p.team_name}`}</TextBlock>
                          </TextBlock>
                        ))}
                        {list.reduce((n, p) => n + Math.max(1, p.phases?.length ?? 0), 0) > 3 && (
                          <TextBlock as="span" className="text-[10px] text-mist">{`+${list.reduce((n, p) => n + Math.max(1, p.phases?.length ?? 0), 0) - 3} lagi`}</TextBlock>
                        )}
                      </div>
                    </>
                  )}
                </ActionButton>
              );
            })}
          </div>
        </div>

      </QueryState>

      <ConfirmDialog
        open={bulkOpen}
        title="Hapus jadwal terpilih?"
        message={`${sel.length} jadwal beserta pekerjaannya akan dihapus dan tidak dapat dikembalikan. Jadwal yang sudah dimulai atau dipakai tidak ikut terhapus dan dilaporkan.`}
        confirmLabel="Hapus"
        danger
        busy={bulkBusy}
        onConfirm={bulkDelete}
        onClose={() => setBulkOpen(false)}
      />

      {dayOpen && (
        <VmsDialog open title={LONG.format(asDate(picked))} onClose={() => setDayOpen(false)}>
          <div className="space-y-2">
            {picked < today && (
              <TextBlock as="p" className="text-xs text-mist">
                {`Tanggal lampau: jadwal baru hanya sampai ${BACKDATE_DAYS} hari ke belakang dan wajib beralasan.`}
              </TextBlock>
            )}
            {rows.map((team) => {
              const plan = dayPlans.find((p) => p.team_id === team.team_id);
              if (!plan) {
                // Tim tanpa jadwal pada tanggal ini: tombol buat (tanggal lampau sampai BACKDATE_DAYS hari, PM/OM).
                if (only || !canPlan || picked < addDays(today, -BACKDATE_DAYS)) return null;
                return (
                  <ActionButton key={team.team_id} variant="outline" className="w-full justify-between border-dashed text-mist"
                    onClick={() => { setDayOpen(false); onCreate(team, picked); }}>
                    <TextBlock as="span">{team.name}</TextBlock>
                    <TextBlock as="span">Kosong · + Buat jadwal</TextBlock>
                  </ActionButton>
                );
              }
              const pct = displayPct(plan);
              const color = phaseColor(mainPhase(plan));
              const card = (
                <ActionButton key={team.team_id} variant="outline"
                  className="relative flex h-auto w-full flex-col items-stretch gap-1.5 overflow-hidden whitespace-normal p-3 pl-4 text-left"
                  onClick={() => { setDayOpen(false); onOpen(plan); }}>
                  <TextBlock as="span" className={`absolute inset-y-0 left-0 w-1.5 ${color.bar}`} />
                  <div className="flex justify-between gap-2">
                    <TextBlock as="span" className="truncate font-semibold">{`${team.name} · ${plan.site_name || "Lokasi belum ditentukan"}`}</TextBlock>
                    <TextBlock as="span" className={`font-semibold ${WORK_STATE[workState(plan, today)].text}`}>{`${WORK_STATE[workState(plan, today)].label} · ${pct}%`}</TextBlock>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-line">
                    <div className={`h-full rounded-full ${WORK_STATE[workState(plan, today)].bar}`} style={{ width: `${pct}%` }} />
                  </div>
                  <TextBlock as="span" className="text-xs text-mist">
                    {`${(plan.phases ?? []).map(phaseLabel).join(", ")} · ${plan.done_count} dari ${plan.item_count} pekerjaan selesai`}
                  </TextBlock>
                </ActionButton>
              );
              if (!deletable(plan)) return card;
              const checked = sel.includes(plan.daily_plan_id);
              return (
                <div key={team.team_id} className="flex items-start gap-2">
                  <CheckControl className="mt-4" aria-label={`Pilih jadwal ${team.name}`} checked={checked}
                    onCheckedChange={(v) => setSel((old) => (v === true ? [...old, plan.daily_plan_id] : old.filter((x) => x !== plan.daily_plan_id)))} />
                  <div className="min-w-0 flex-1">{card}</div>
                </div>
              );
            })}
            {sel.length > 0 && (
              <div className="flex items-center justify-between gap-2 border-t border-line pt-2">
                <TextBlock as="span" className="text-xs text-mist">{`${sel.length} jadwal dipilih`}</TextBlock>
                <ActionButton variant="destructive" disabled={bulkBusy} onClick={() => setBulkOpen(true)}>
                  {`Hapus terpilih (${sel.length})`}
                </ActionButton>
              </div>
            )}
          </div>
        </VmsDialog>
      )}
    </div>
  );
}
