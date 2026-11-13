import { z } from "zod";

/** Form "Perbarui dokumen". Batas sama dengan VehicleDocumentCreate di API (doc_no 100, catatan 500). */
export const vehicleDocumentSchema = z
  .object({
    doc_type_code: z.string().min(1, "Pilih jenis dokumen."),
    doc_no: z.string().trim().max(100, "Nomor dokumen maksimal 100 karakter."),
    issued_on: z.string(),
    expired_on: z.string().min(1, "Tanggal jatuh tempo wajib diisi."),
    catatan: z.string().trim().max(500, "Catatan maksimal 500 karakter."),
  })
  .refine((v) => !v.issued_on || !v.expired_on || v.issued_on <= v.expired_on, {
    path: ["issued_on"],
    message: "Tanggal berlaku harus sebelum tanggal jatuh tempo.",
  });
export type VehicleDocumentValues = z.infer<typeof vehicleDocumentSchema>;
