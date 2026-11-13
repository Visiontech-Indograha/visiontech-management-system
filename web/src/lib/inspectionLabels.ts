/** Label layar untuk inspeksi kendaraan (kode API tetap di kode, bukan di layar). */
export const PERIOD_LABEL: Record<string, string> = { DAILY: "Harian", WEEKLY: "Mingguan", MONTHLY: "Bulanan" };
export const INSPECTION_STATUS_LABEL: Record<string, string> = {
  SUBMITTED: "Menunggu pemeriksaan HSE",
  VERIFIED: "Sudah diperiksa HSE",
  REJECTED: "Ditolak HSE",
};
export const ANSWER_LABEL: Record<string, string> = { BAIK: "Baik", PERLU_PERBAIKAN: "Perlu perbaikan", RUSAK: "Rusak" };

export const periodLabel = (v: string) => PERIOD_LABEL[v] ?? v;
export const inspectionStatusLabel = (v: string) => INSPECTION_STATUS_LABEL[v] ?? v;
export const answerLabel = (v: unknown) => (typeof v === "string" ? (ANSWER_LABEL[v] ?? v) : "-");
export const inspectionStatusTone = (v: string): "success" | "warning" | "danger" | "neutral" =>
  v === "VERIFIED" ? "success" : v === "REJECTED" ? "danger" : v === "SUBMITTED" ? "warning" : "neutral";
