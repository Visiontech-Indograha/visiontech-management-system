import { PHASES, PHASE_LABEL, type Phase } from "@/lib/workPhase";

/** Ringkasan pratinjau template foto: jumlah slot, yang wajib, dan yang sudah punya foto contoh. */
export function slotSummary(photos: ReadonlyArray<{ required?: boolean | null; example_file_id?: string | null }>): string {
  if (photos.length === 0) return "Tanpa template foto";
  const wajib = photos.filter((p) => p.required).length;
  const contoh = photos.filter((p) => p.example_file_id).length;
  return `${photos.length} slot · ${wajib} wajib · ${contoh} dengan contoh`;
}

/** Fase bawaan yang boleh dipilih untuk satu peran: survei hanya untuk jenis survei (sama dengan API). */
export function defaultPhaseOptions(kind: string): Phase[] {
  const survey = kind === "SURVEY_TASK" || kind === "SURVEY_POINT";
  return PHASES.filter((p) => (p === "SURVEY" ? survey : true));
}

/** Label satuan & fase untuk kartu: fase kosong berarti mengikuti peran. */
export function defaultsLabel(unit: string | null | undefined, phase: string | null | undefined): string {
  const fase = phase ? PHASE_LABEL[phase as Phase] ?? phase : "mengikuti peran";
  return `Satuan: ${unit || "Unit"} · Fase bawaan: ${fase}`;
}
