import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { ControlInput } from "@/components/molecules/FormBlock";
import { CalendarDays, ClipboardCheck, MapPin, Plus, X } from "@/components/molecules/Glyphs";
import { PlainAction } from "@/components/molecules/PlainAction";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { displayPct, PHASE_COLOR, PHASE_LABEL, PHASES, phaseColor, phaseLabel, WORK_STATE, workState, type Phase } from "@/lib/workPhase";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { addDays, BACKDATE_DAYS, useDailyPlans, useDeleteDailyPlan, weekStart, type DailyPlan } from "@/services/dailyPlanService";

const MONTH = new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric", timeZone: "UTC" });
const LONG = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
const SHORT_DATE = new Intl.DateTimeFormat("id-ID", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
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

export type QuickStatusFilter = "ALL" | "PENDING_APPROVAL" | "ONGOING" | "LATE" | "OUT_OF_TOWN" | "DONE";

export interface MatrixTeam {
  team_id: string;
  name: string;
  division_id: string;
}

/**
 * Kalender bulanan & daftar agenda jadwal tim.
 * Mendukung saringan multi-dimensi (status cepat, jenis pekerjaan, pencarian lokasi/tim)
 * serta pergantian tampilan [ Agenda | Kalender ] yang otomatis memakai Agenda di layar ponsel (< 640 px).
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
  const [statusFilter, setStatusFilter] = useState<QuickStatusFilter>("ALL");
  const [searchQ, setSearchQ] = useState("");
  const [viewMode, setViewMode] = useState<"calendar" | "agenda">(() =>
    typeof window !== "undefined" && window.innerWidth < 640 ? "agenda" : "calendar",
  );
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

  const inMonth = (d: string) => d >= month && d < nextMonth;
  const rawMonthPlans = (plans.data ?? []).filter((p) => inMonth(p.work_date));

  // Hitung ringkasan status untuk pil cepat di atas kalender
  const countPending = rawMonthPlans.filter((p) => p.status === "SUBMITTED").length;
  const countOngoing = rawMonthPlans.filter((p) => workState(p, today) === "ONGOING").length;
  const countLate = rawMonthPlans.filter((p) => workState(p, today) === "LATE").length;
  const countOutOfTown = rawMonthPlans.filter((p) => p.is_out_of_town).length;
  const countDone = rawMonthPlans.filter((p) => workState(p, today) === "DONE").length;

  const qNorm = searchQ.trim().toLowerCase();
  const match = (p: DailyPlan) => {
    if (only && !(p.phases ?? []).includes(only)) return false;
    if (statusFilter === "PENDING_APPROVAL" && p.status !== "SUBMITTED") return false;
    if (statusFilter === "ONGOING" && workState(p, today) !== "ONGOING") return false;
    if (statusFilter === "LATE" && workState(p, today) !== "LATE") return false;
    if (statusFilter === "OUT_OF_TOWN" && !p.is_out_of_town) return false;
    if (statusFilter === "DONE" && workState(p, today) !== "DONE") return false;
    if (qNorm) {
      const hay = `${p.team_name} ${p.site_name ?? ""} ${p.leader_name ?? ""}`.toLowerCase();
      if (!hay.includes(qNorm)) return false;
    }
    return true;
  };

  const all = (plans.data ?? []).filter(match);
  const byDay = new Map<string, DailyPlan[]>();
  for (const p of all) byDay.set(p.work_date, [...(byDay.get(p.work_date) ?? []), p]);
  const rows = teams.length
    ? teams
    : [...new Map((plans.data ?? []).map((p) => [p.team_id, { team_id: p.team_id, name: p.team_name, division_id: p.division_id }])).values()];
  const dayPlans = byDay.get(picked) ?? [];
  const emptyDays = days.filter((d) => inMonth(d) && !byDay.has(d)).length;
  const hasActiveFilter = only !== null || statusFilter !== "ALL" || qNorm.length > 0;

  const statusPills: { key: QuickStatusFilter; label: string; count: number; tone?: string }[] = [
    { key: "ALL", label: "Semua", count: rawMonthPlans.length },
    ...(countPending > 0 ? [{ key: "PENDING_APPROVAL" as const, label: "Perlu disetujui", count: countPending, tone: "border-warning-border bg-warning-bg text-warning" }] : []),
    { key: "ONGOING", label: "Berjalan", count: countOngoing, tone: "border-info-border bg-info-bg text-info" },
    ...(countLate > 0 ? [{ key: "LATE" as const, label: "Terlambat", count: countLate, tone: "border-danger-border bg-danger-bg text-danger" }] : []),
    { key: "OUT_OF_TOWN", label: "Luar kota", count: countOutOfTown },
    { key: "DONE", label: "Selesai", count: countDone, tone: "border-success-border bg-success-bg text-success" },
  ];

  const monthDaysWithPlans = days.filter((d) => inMonth(d) && (byDay.get(d)?.length ?? 0) > 0);

  return (
    <div className="space-y-4">
      {/* Baris 1: Navigasi bulan + Pencarian cepat + Sakelar tampilan [Agenda | Kalender] */}
      <div className="flex flex-col gap-3 rounded-panel border border-line bg-surface p-3 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <ActionButton size="sm" variant="outline" aria-label="Bulan sebelumnya" onClick={() => setMonth(shiftMonth(month, -1))}>‹</ActionButton>
            <TextBlock as="h3" className="min-w-36 text-center text-base font-semibold capitalize">{MONTH.format(asDate(month))}</TextBlock>
            <ActionButton size="sm" variant="outline" aria-label="Bulan berikutnya" onClick={() => setMonth(shiftMonth(month, 1))}>›</ActionButton>
            <ActionButton size="sm" variant="ghost" onClick={() => { setMonth(`${today.slice(0, 7)}-01`); setPicked(today); }}>Bulan ini</ActionButton>
          </div>

          <div className="flex flex-1 flex-wrap items-center justify-end gap-2">
            <div className="relative min-w-48 flex-1 sm:max-w-64">
              <ControlInput
                type="search"
                aria-label="Cari lokasi atau nama tim"
                placeholder="Cari lokasi atau tim..."
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                className="h-9 w-full rounded-control border border-line bg-background pl-3 pr-8 text-xs focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
              />
              {searchQ && (
                <PlainAction
                  type="button"
                  aria-label="Bersihkan pencarian jadwal"
                  onClick={() => setSearchQ("")}
                  className="absolute right-1.5 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full text-mist hover:bg-hover hover:text-ink"
                >
                  <X size={13} />
                </PlainAction>
              )}
            </div>

            <div className="inline-flex rounded-control border border-line bg-background p-0.5" role="group" aria-label="Mode tampilan jadwal">
              <ActionButton
                size="xs"
                variant={viewMode === "agenda" ? "default" : "ghost"}
                onClick={() => setViewMode("agenda")}
                className="gap-1 rounded-sm px-2.5"
              >
                <ClipboardCheck size={13} />
                Agenda
              </ActionButton>
              <ActionButton
                size="xs"
                variant={viewMode === "calendar" ? "default" : "ghost"}
                onClick={() => setViewMode("calendar")}
                className="gap-1 rounded-sm px-2.5"
              >
                <CalendarDays size={13} />
                Kalender
              </ActionButton>
            </div>
          </div>
        </div>

        {/* Baris 2: Pil Ringkasan Status (1 ketukan untuk menyaring) */}
        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5" role="group" aria-label="Filter status jadwal">
          {statusPills.map((pill) => {
            const active = statusFilter === pill.key;
            return (
              <ActionButton
                key={pill.key}
                size="xs"
                variant={active ? "default" : "outline"}
                onClick={() => setStatusFilter(active && pill.key !== "ALL" ? "ALL" : pill.key)}
                className={`shrink-0 rounded-full px-3 text-xs ${!active && pill.tone ? pill.tone : ""}`}
              >
                {`${pill.label} (${pill.count})`}
              </ActionButton>
            );
          })}
        </div>

        {/* Baris 3: Filter Jenis Pekerjaan + Tombol Atur Ulang */}
        <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto" role="group" aria-label="Jenis pekerjaan">
          <ActionButton size="xs" className="shrink-0 rounded-full" variant={only === null ? "default" : "outline"} onClick={() => setOnly(null)}>Semua jenis</ActionButton>
          {PHASES.map((ph) => (
            <ActionButton
              key={ph}
              size="xs"
              variant="outline"
              className={`shrink-0 rounded-full border ${PHASE_COLOR[ph].chip} ${only === ph ? "ring-2 ring-ink" : only ? "opacity-50" : ""}`}
              onClick={() => setOnly(only === ph ? null : ph)}
            >
              <TextBlock as="span" className={`mr-1.5 inline-block h-2 w-2 rounded-full ${PHASE_COLOR[ph].dot}`} />
              {PHASE_LABEL[ph]}
            </ActionButton>
          ))}
          {hasActiveFilter && (
            <ActionButton
              size="xs"
              variant="ghost"
              className="ml-auto shrink-0 text-xs text-primary underline-offset-2 hover:underline"
              onClick={() => {
                setOnly(null);
                setStatusFilter("ALL");
                setSearchQ("");
              }}
            >
              Atur ulang filter
            </ActionButton>
          )}
        </div>
      </div>

      <QueryState query={plans} errorText="Jadwal tidak dapat dimuat.">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <TextBlock as="p" className="text-sm text-mist">
            {`${all.filter((p) => inMonth(p.work_date)).length} jadwal ditampilkan · ${emptyDays} hari kosong`}
          </TextBlock>
          {canPlan && (
            <ActionButton
              size="sm"
              variant="outline"
              onClick={() => {
                setPicked(today);
                setDayOpen(true);
              }}
              className="gap-1.5"
            >
              <Plus size={15} />
              Jadwal hari ini
            </ActionButton>
          )}
        </div>

        {viewMode === "agenda" ? (
          /* Tampilan Agenda (Default di Ponsel): Kartu harian penuh yang mudah dibaca & diketuk */
          <div className="space-y-3">
            {monthDaysWithPlans.length === 0 ? (
              <div className="rounded-panel border border-dashed border-line bg-surface p-8 text-center">
                <TextBlock className="font-medium text-ink">Tidak ada jadwal yang cocok pada bulan ini.</TextBlock>
                <TextBlock className="mt-1 text-xs text-mist">
                  Ubah filter di atas atau beralih ke tampilan Kalender untuk membuat jadwal baru pada tanggal tertentu.
                </TextBlock>
              </div>
            ) : (
              monthDaysWithPlans.map((d) => {
                const list = byDay.get(d) ?? [];
                const isToday = d === today;
                return (
                  <div
                    key={d}
                    className={`rounded-panel border bg-surface p-3.5 shadow-card ${isToday ? "border-primary ring-1 ring-primary/30" : "border-line"}`}
                  >
                    <div className="mb-2.5 flex items-center justify-between gap-2 border-b border-line pb-2">
                      <div className="flex items-center gap-2">
                        <TextBlock as="h4" className="text-sm font-semibold capitalize text-ink">
                          {SHORT_DATE.format(asDate(d))}
                        </TextBlock>
                        {isToday && (
                          <TextBlock as="span" className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                            Hari ini
                          </TextBlock>
                        )}
                      </div>
                      {canPlan && (
                        <ActionButton
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setPicked(d);
                            setDayOpen(true);
                          }}
                        >
                          {`Kelola hari (${list.length})`}
                        </ActionButton>
                      )}
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {list.map((plan) => {
                        const pct = displayPct(plan);
                        const st = WORK_STATE[workState(plan, today)];
                        const color = phaseColor(mainPhase(plan));
                        return (
                          <ActionButton
                            key={plan.daily_plan_id}
                            variant="outline"
                            onClick={() => onOpen(plan)}
                            className="relative flex h-auto w-full flex-col items-stretch gap-1.5 overflow-hidden whitespace-normal rounded-lg p-3 pl-4 text-left hover:border-primary/40"
                          >
                            <TextBlock as="span" className={`absolute inset-y-0 left-0 w-1.5 ${color.bar}`} />
                            <div className="flex items-start justify-between gap-2">
                              <TextBlock as="span" className="font-semibold text-ink">
                                {plan.team_name}
                              </TextBlock>
                              <TextBlock as="span" className={`shrink-0 text-xs font-semibold ${st.text}`}>
                                {`${st.label} · ${pct}%`}
                              </TextBlock>
                            </div>
                            <div className="flex items-center gap-1 text-xs text-mist">
                              <MapPin size={12} className="shrink-0" />
                              <TextBlock as="span" className="truncate">
                                {plan.site_name || "Lokasi belum ditentukan"}
                              </TextBlock>
                              {plan.is_out_of_town && (
                                <TextBlock as="span" className="ml-1 shrink-0 rounded-full border border-warning-border bg-warning-bg px-1.5 py-0.2 text-[10px] font-semibold text-warning">
                                  Luar kota
                                </TextBlock>
                              )}
                            </div>
                            <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
                              <div className={`h-full rounded-full ${st.bar}`} style={{ width: `${pct}%` }} />
                            </div>
                            <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-mist">
                              <TextBlock as="span" className="truncate font-medium">
                                {(plan.phases ?? []).map(phaseLabel).join(", ") || "Persiapan"}
                              </TextBlock>
                              <TextBlock as="span">
                                {`${plan.done_count}/${plan.item_count} selesai`}
                              </TextBlock>
                            </div>
                          </ActionButton>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        ) : (
          /* Tampilan Kalender Bulanan */
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
        )}

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
                    <TextBlock as="span" className="truncate font-semibold">
                      {`${team.name} · ${plan.site_name || "Lokasi belum ditentukan"}${plan.is_out_of_town ? " · Luar kota" : ""}`}
                    </TextBlock>
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
