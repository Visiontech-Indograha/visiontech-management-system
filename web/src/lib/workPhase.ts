/** Jenis pekerjaan per item jadwal — satu sumber label & warna untuk semua layar (bahasa yang dipakai di lapangan). */
export const PHASES = ["SURVEY", "PREPARATION", "INSTALLATION", "REPLACEMENT", "MAINTENANCE"] as const;
export type Phase = (typeof PHASES)[number];

export const PHASE_LABEL: Record<Phase, string> = {
  SURVEY: "Survei",
  PREPARATION: "Persiapan",
  INSTALLATION: "Instalasi",
  REPLACEMENT: "Penggantian",
  MAINTENANCE: "Pemeliharaan",
};

export const PHASE_TONE: Record<Phase, "info" | "neutral" | "success" | "warning" | "danger"> = {
  SURVEY: "info",
  PREPARATION: "neutral",
  INSTALLATION: "success",
  REPLACEMENT: "warning",
  MAINTENANCE: "danger",
};

export const phaseLabel = (p: string) => PHASE_LABEL[p as Phase] ?? p;

/** Warna per jenis — token palet Visiontech (docs/18): Survei info, Persiapan netral, Instalasi success,
 * Replacement warning, Maintenance brand. Dipakai kalender agar jenis langsung terbedakan. */
export const PHASE_COLOR: Record<Phase, { dot: string; chip: string; bar: string }> = {
  SURVEY: { dot: "bg-info-solid", chip: "bg-info-bg text-info border-info-border", bar: "bg-info-solid" },
  PREPARATION: { dot: "bg-neutral-500", chip: "bg-neutral-100 text-neutral-700 border-neutral-300", bar: "bg-neutral-500" },
  INSTALLATION: { dot: "bg-success-solid", chip: "bg-success-bg text-success border-success-border", bar: "bg-success-solid" },
  REPLACEMENT: { dot: "bg-warning-solid", chip: "bg-warning-bg text-warning border-warning-border", bar: "bg-warning-solid" },
  MAINTENANCE: { dot: "bg-brand-500", chip: "bg-brand-50 text-brand-700 border-brand-200", bar: "bg-brand-500" },
};
export const phaseColor = (p: string) => PHASE_COLOR[p as Phase] ?? PHASE_COLOR.PREPARATION;

/** Keadaan kerja satu jadwal: biru berjalan, merah terlambat, hijau selesai, kuning selesai sebagian, abu belum mulai. */
export type WorkState = "NOT_STARTED" | "ONGOING" | "LATE" | "PARTIAL" | "DONE";
export const WORK_STATE: Record<WorkState, { label: string; dot: string; text: string; bar: string }> = {
  NOT_STARTED: { label: "Belum mulai", dot: "bg-neutral-400", text: "text-neutral-600", bar: "bg-neutral-400" },
  ONGOING: { label: "Berjalan", dot: "bg-info-solid", text: "text-info", bar: "bg-info-solid" },
  LATE: { label: "Terlambat", dot: "bg-danger-solid", text: "text-danger", bar: "bg-danger-solid" },
  PARTIAL: { label: "Selesai sebagian", dot: "bg-warning-solid", text: "text-warning", bar: "bg-warning-solid" },
  DONE: { label: "Selesai", dot: "bg-success-solid", text: "text-success", bar: "bg-success-solid" },
};
/** Persen yang ditampilkan. API menghitung rata-rata per item (DONE 100%, pindah hari 0%, lainnya
 * dikerjakan/target, dibulatkan ke bawah); klien hanya membatasi ke 99 selama belum semua item DONE. */
export function displayPct(p: { done_count: number; item_count: number; progress_pct?: number }): number {
  const raw = p.progress_pct ?? (p.item_count ? (p.done_count / p.item_count) * 100 : 0);
  const pct = Math.max(0, Math.min(100, Math.round(raw)));
  const allDone = p.item_count > 0 && p.done_count >= p.item_count;
  return !allDone && pct >= 100 ? 99 : pct;
}

export function workState(
  p: { status: string; work_date: string; done_count: number; item_count: number; progress_pct?: number },
  today: string,
): WorkState {
  const pct = displayPct(p);
  if (p.status === "DONE" || (p.item_count > 0 && p.done_count >= p.item_count)) return "DONE";
  if (p.status === "COMPLETED") return pct > 0 ? "PARTIAL" : "DONE";
  if (p.work_date < today) return "LATE";
  if (p.status === "ONGOING" || pct > 0) return "ONGOING";
  return "NOT_STARTED";
}
