import { z } from "zod";

/** Batas sama dengan api/app/modules/divisions/schemas/division_schema.py. */
export const divisionSchema = z.object({
  name: z.string().trim().min(2, "Nama divisi minimal 2 karakter.").max(100, "Nama divisi maksimal 100 karakter."),
  om_id: z.string().min(1, "Pilih Operational Manager."),
  pm_id: z.string().min(1, "Pilih Project Manager."),
});
export type DivisionValues = z.infer<typeof divisionSchema>;

/** Batas sama dengan api/app/modules/job_positions/schemas/job_position_schema.py. */
export const positionSchema = z.object({
  code: z.string().trim().min(1, "Kode wajib diisi.").max(30, "Kode maksimal 30 karakter."),
  name: z.string().trim().min(2, "Nama jabatan minimal 2 karakter.").max(100, "Nama jabatan maksimal 100 karakter."),
  grade_level: z
    .number({ message: "Isi dengan angka 1 sampai 20." })
    .int("Isi dengan angka bulat.")
    .min(1, "Tingkat minimal 1.")
    .max(20, "Tingkat maksimal 20."),
});
export type PositionValues = z.infer<typeof positionSchema>;
