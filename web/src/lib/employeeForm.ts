import { z } from "zod";

/** Data kerja karyawan V2 (Milestone 10): dipakai form tambah & ubah karyawan. */
export const employeeFormSchema = z
  .object({
    employee_no: z.string().trim().min(2, "No. karyawan minimal 2 karakter.").max(50, "No. karyawan maksimal 50 karakter."),
    full_name: z.string().trim().min(2, "Nama lengkap minimal 2 karakter.").max(150, "Nama lengkap maksimal 150 karakter."),
    office_id: z.string().min(1, "Pilih kantor."),
    division_id: z.string(),
    position_id: z.string(),
    join_date: z.string().min(1, "Tanggal bergabung wajib diisi."),
    pkwt_end_date: z.string(),
  })
  .refine((v) => !v.pkwt_end_date || v.pkwt_end_date >= v.join_date, {
    path: ["pkwt_end_date"],
    message: "Akhir PKWT tidak boleh sebelum tanggal bergabung.",
  });
export type EmployeeFormValues = z.infer<typeof employeeFormSchema>;
export const EMPLOYEE_FORM_FIELDS = [
  "employee_no", "full_name", "office_id", "division_id", "position_id", "join_date", "pkwt_end_date",
] as const;
