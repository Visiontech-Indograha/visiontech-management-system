import type { components } from "@/lib/apiTypes";
const addDays = (iso: string, days: number): string => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
};

/** Kunci sel "tim|tanggal" untuk pilihan massal. */
export const cellKey = (teamId: string, workDate: string) => `${teamId}|${workDate}`;

/** Alokasi mingguan (PM/OM): kategori sel matriks, label Bahasa Indonesia, dan penyusun permintaan API. */
export type WeeklyMatrix = components["schemas"]["WeeklyMatrixOut"];
export type WeeklyRow = components["schemas"]["WeeklyRow"];
export type WeeklyCell = components["schemas"]["WeeklyCell"];
export type BulkOut = components["schemas"]["DailyBulkOut"];
export type BulkCell = components["schemas"]["DailyBulkCellOut"];
export type PlanItemInput = components["schemas"]["PlanItemCreate"];

/** Sel SIAGA = jadwal kind STANDBY (menunggu perintah PM); sisanya mengikuti status jadwal. */
export type CellKind = "EMPTY" | "DRAFT" | "SUBMITTED" | "APPROVED" | "ONGOING" | "COMPLETED" | "STANDBY";

export const CELL_LABEL: Record<CellKind, string> = {
  EMPTY: "Kosong",
  DRAFT: "Draf",
  SUBMITTED: "Diajukan",
  APPROVED: "Disetujui",
  ONGOING: "Berjalan",
  COMPLETED: "Selesai",
  STANDBY: "SIAGA",
};

/** Kelas warna per kategori; hanya token tema (tanpa warna mentah) agar konsisten terang/gelap. */
export const CELL_TONE: Record<CellKind, string> = {
  EMPTY: "border-dashed border-neutral-300 bg-transparent text-neutral-500",
  DRAFT: "border-neutral-300 bg-neutral-100 text-neutral-700",
  SUBMITTED: "border-info-border bg-info-bg text-info",
  APPROVED: "border-success-border bg-success-bg text-success",
  ONGOING: "border-brand-200 bg-brand-50 text-brand-700",
  COMPLETED: "border-neutral-400 bg-neutral-200 text-neutral-800",
  STANDBY: "border-warning-border bg-warning-bg text-warning",
};

export const CELL_KINDS: CellKind[] = ["EMPTY", "DRAFT", "SUBMITTED", "APPROVED", "ONGOING", "COMPLETED", "STANDBY"];

export function cellKind(cell: WeeklyCell): CellKind {
  if (!cell.daily_plan_id) return "EMPTY";
  if (cell.kind === "STANDBY") return "STANDBY";
  return (cell.status ?? "DRAFT") as CellKind;
}

export const DAY_LABEL = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

const LONG = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
export const longDate = (iso: string) => LONG.format(new Date(`${iso}T00:00:00Z`));

/** Tanggal ISO dari rentang (inklusif). `skipWeekend` = hanya hari kerja Senin–Jumat. */
export function datesBetween(start: string, end: string, skipWeekend: boolean): string[] {
  const out: string[] = [];
  for (let d = start; d <= end; d = addDays(d, 1)) {
    const dow = new Date(`${d}T00:00:00Z`).getUTCDay();
    if (!skipWeekend || (dow !== 0 && dow !== 6)) out.push(d);
  }
  return out;
}

/** Batas API: satu permintaan bulk memuat paling banyak 31 tanggal dan 30 tim. */
export const MAX_DATES = 31;
export const MAX_TEAMS = 30;

export function validateRange(start: string, end: string): string | null {
  if (!start || !end) return "Isi tanggal mulai dan selesai.";
  if (end < start) return "Tanggal selesai harus sama atau setelah tanggal mulai.";
  if (datesBetween(start, end, false).length > MAX_DATES) return `Rentang maksimal ${MAX_DATES} hari.`;
  return null;
}

/** Sel kosong pada matriks yang belum lewat (dipakai "Siaga hari kosong"). */
export function emptyCells(matrix: WeeklyMatrix, today: string): { team_id: string; work_date: string }[] {
  const out: { team_id: string; work_date: string }[] = [];
  for (const row of matrix.rows) {
    for (const cell of row.cells) {
      if (!cell.daily_plan_id && cell.work_date >= today) out.push({ team_id: row.team_id, work_date: cell.work_date });
    }
  }
  return out;
}

/** Grup siaga per divisi: tim × tanggal kosong (sel yang sudah terisi dilewati API). Satu permintaan per divisi. */
export interface StandbyGroup {
  division_id: string;
  team_ids: string[];
  work_dates: string[];
}
export function standbyGroups(matrix: WeeklyMatrix, today: string): StandbyGroup[] {
  return matrix.divisions
    .map((d) => {
      const cells = emptyCells({ ...matrix, rows: matrix.rows.filter((r) => r.division_id === d.division_id) }, today);
      return {
        division_id: d.division_id,
        team_ids: [...new Set(cells.map((c) => c.team_id))],
        work_dates: [...new Set(cells.map((c) => c.work_date))].sort(),
      };
    })
    .filter((g) => g.team_ids.length > 0);
}

export function summarizeBulk(out: BulkOut) {
  const warnings = out.cells.reduce((n, c) => n + (c.warnings ?? []).length, 0);
  return { created: out.created, skipped: out.skipped, warnings };
}

/** Pesan satu sel hasil: berhasil (+peringatan) atau dilewati beserta alasan. */
export function cellResultText(c: BulkCell): string {
  if (c.status === "CREATED") {
    const w = (c.warnings ?? []).map((x) => x.message);
    return ["Dibuat", ...w].join(". ");
  }
  return c.message ?? "Dilewati.";
}

/** Pekerjaan yang ditambahkan ke tiap jadwal yang baru dibuat (satu item per tim-hari). */
export function itemPayload(input: {
  workTypeId: string;
  title: string;
  completionId: string;
  target: number;
  location: string;
}): PlanItemInput {
  return {
    work_type_id: input.workTypeId,
    title: input.title.trim(),
    is_main_deliverable: true,
    completion_id: input.completionId,
    target_qty: input.target,
    location_name: input.location.trim() || null,
  } as PlanItemInput;
}

/** Salin minggu: setiap jadwal minggu ini disalin ke tanggal +7 hari. */
export function copyWeekTargets(matrix: WeeklyMatrix): { daily_plan_id: string; work_date: string }[] {
  const out: { daily_plan_id: string; work_date: string }[] = [];
  for (const row of matrix.rows) {
    for (const cell of row.cells) {
      if (cell.daily_plan_id) out.push({ daily_plan_id: cell.daily_plan_id, work_date: addDays(cell.work_date, 7) });
    }
  }
  return out;
}
