import { z } from "zod";

/** Batas sama dengan hse_schema.py di API (catatan 1000, foto 10, odometer 0..10.000.000, jenis periode). */
export const INSPECTION_MAX_NOTES = 1000;
export const INSPECTION_MAX_PHOTOS = 10;
export const INSPECTION_MAX_ODOMETER = 10_000_000;
export const PERIOD_TYPES = ["DAILY", "WEEKLY", "MONTHLY"] as const;

export const inspectionSchema = z.object({
  vehicle_id: z.string().min(1, "Pilih kendaraan."),
  period_type: z.enum(PERIOD_TYPES, { message: "Pilih jenis pemeriksaan." }),
  odometer_km: z
    .string()
    .trim()
    .refine((v) => v === "" || (/^\d+$/.test(v) && Number(v) <= INSPECTION_MAX_ODOMETER), "Isi angka 0 sampai 10.000.000."),
  notes: z.string().trim().max(INSPECTION_MAX_NOTES, `Catatan maksimal ${INSPECTION_MAX_NOTES} karakter.`),
});
export type InspectionValues = z.infer<typeof inspectionSchema>;

/** Alasan wajib saat menolak; maksimal sama dengan catatan di API. */
export const rejectReasonSchema = z.string().trim().min(1, "Tulis alasan penolakan.").max(INSPECTION_MAX_NOTES, `Alasan maksimal ${INSPECTION_MAX_NOTES} karakter.`);

/** Pesan galat bila butir daftar periksa belum semua dijawab atau foto terlalu banyak; null bila lolos. */
export function checklistBlocker(keys: string[], answers: Record<string, string>, photoCount: number): string | null {
  if (keys.some((k) => !answers[k])) return "Semua butir pemeriksaan harus dijawab.";
  if (photoCount > INSPECTION_MAX_PHOTOS) return `Foto bukti maksimal ${INSPECTION_MAX_PHOTOS}.`;
  return null;
}
