import type { components } from "@/lib/apiTypes";

export type StatusBanding = components["schemas"]["BandingBaris"]["status"];
export const STATUS_BANDING: readonly StatusBanding[] = ["cocok", "waktu_berbeda", "hanya_mesin", "hanya_aplikasi"];

export const STATUS_LABEL: Record<StatusBanding, string> = {
  cocok: "Cocok",
  waktu_berbeda: "Waktu berbeda",
  hanya_mesin: "Hanya di mesin",
  hanya_aplikasi: "Hanya di aplikasi",
};

export const STATUS_TONE: Record<StatusBanding, "success" | "warning" | "info"> = {
  cocok: "success",
  waktu_berbeda: "warning",
  hanya_mesin: "info",
  hanya_aplikasi: "info",
};

/** Kalimat selisih awam: "3 menit lebih lambat di mesin". "-" = tidak ada pembanding. */
export function selisihLabel(menit: number | null): string {
  if (menit == null) return "-";
  if (menit === 0) return "Sama";
  return `${Math.abs(menit)} menit ${menit > 0 ? "lebih lambat" : "lebih awal"} di mesin`;
}
