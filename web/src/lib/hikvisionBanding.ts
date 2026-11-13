import type { components } from "@/lib/apiTypes";

type BandingBaris = components["schemas"]["BandingBaris"];

/** Selisih waktu (menit) yang masih dianggap sama antara mesin dan aplikasi. */
export const TOLERANSI_MENIT = 5;

export type StatusBanding = "cocok" | "selisih" | "hanya_mesin";
export const STATUS_BANDING: readonly StatusBanding[] = ["cocok", "selisih", "hanya_mesin"];

export const STATUS_LABEL: Record<StatusBanding, string> = {
  cocok: "Cocok",
  selisih: "Waktu berbeda",
  hanya_mesin: "Hanya di mesin",
};

export const STATUS_TONE: Record<StatusBanding, "success" | "warning" | "info"> = {
  cocok: "success",
  selisih: "warning",
  hanya_mesin: "info",
};

/** Tanpa absen aplikasi = hanya di mesin; selisih melewati toleransi = waktu berbeda; selain itu cocok. */
export function statusBanding(r: BandingBaris): StatusBanding {
  if (!r.clock_in_at && !r.clock_out_at) return "hanya_mesin";
  const beda = [r.selisih_masuk_menit, r.selisih_pulang_menit].some((m) => m != null && Math.abs(m) > TOLERANSI_MENIT);
  return beda ? "selisih" : "cocok";
}

/** Kalimat selisih awam: "3 menit lebih lambat di mesin". "-" = tidak ada pembanding. */
export function selisihLabel(menit: number | null): string {
  if (menit == null) return "-";
  if (menit === 0) return "Sama";
  return `${Math.abs(menit)} menit ${menit > 0 ? "lebih lambat" : "lebih awal"} di mesin`;
}

const fold = (v: string) => v.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Cari = awalan nama karyawan (tanpa huruf besar/aksen). */
export const cocokAwalan = (nama: string, q: string) => !q || fold(nama).startsWith(fold(q));
