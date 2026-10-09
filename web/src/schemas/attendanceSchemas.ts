import { z } from "zod";

/** Validasi form tinjau absensi dan penjelasan absensi. */
export const reviewSchema = z.object({
  decision: z.enum(["APPROVE", "REJECT"]),
  note: z.string().trim().min(1, "Catatan pemeriksaan wajib diisi."),
});
export type ReviewValues = z.infer<typeof reviewSchema>;

export const explainSchema = z.object({ explanation: z.string().trim().min(1, "Penjelasan wajib diisi.") });
