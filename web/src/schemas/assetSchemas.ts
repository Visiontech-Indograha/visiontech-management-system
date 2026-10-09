import { z } from "zod";

/** Validasi form aset: tambah aset, lepas reservasi, periksa kendaraan, ajukan & periksa pengembalian. */
export const createSchema = z
  .object({
    kind: z.enum(["VEHICLE", "TOOL"]),
    vehicle_type: z.string().trim(),
    code: z.string().trim().min(1, "Kode aset wajib diisi."),
    name: z.string().trim().min(1, "Nama aset wajib diisi."),
    condition: z.string().trim().min(1, "Kondisi wajib diisi."),
  })
  .refine((v) => v.kind === "TOOL" || v.vehicle_type.length > 0, { path: ["vehicle_type"], message: "Jenis kendaraan wajib diisi." });
export type CreateValues = z.infer<typeof createSchema>;

export const releaseSchema = z.object({ work_plan_id: z.string().min(1, "Pilih work plan.") });

export const checkSchema = z
  .object({ decision: z.enum(["ACCEPT", "APPEAL"]), reason: z.string().trim() })
  .refine((v) => v.decision === "ACCEPT" || v.reason.length > 0, { path: ["reason"], message: "Alasan banding kelayakan wajib diisi." });
export type CheckValues = z.infer<typeof checkSchema>;

export const returnSchema = z.object({
  condition_on_return: z.string().trim().min(1, "Kondisi saat dikembalikan wajib diisi."),
  note: z.string().trim(),
});
export type ReturnValues = z.infer<typeof returnSchema>;

export const verifySchema = z
  .object({ decision: z.enum(["ACCEPT", "REJECT"]), note: z.string().trim() })
  .refine((v) => v.decision === "ACCEPT" || v.note.length > 0, { path: ["note"], message: "Alasan penolakan wajib diisi." });
export type VerifyValues = z.infer<typeof verifySchema>;
