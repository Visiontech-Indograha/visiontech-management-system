import { z } from "zod";

/** Validasi form editor rencana kerja (membuat, menyunting draf, merevisi). Server tetap memeriksa ulang. */
const required = (msg: string) => z.string().trim().min(1, msg);
const fileSchema = z.object({ file_id: z.string(), file_name: z.string() });
const taskSchema = z.object({
  title: required("Judul pekerjaan wajib diisi."),
  description: required("Deskripsi pekerjaan wajib diisi."),
  files: z.array(fileSchema),
});
export const planEditorSchema = z
  .object({
    title: required("Judul pekerjaan wajib diisi."),
    description: required("Deskripsi pekerjaan keseluruhan wajib diisi."),
    category: required("Pilih kategori pekerjaan."),
    site_id: z.string(),
    period_start: required("Tanggal mulai wajib diisi."),
    period_end: required("Tanggal selesai wajib diisi."),
    days: z.array(
      z.object({
        work_date: z.string(),
        tasks: z.array(taskSchema).min(1, "Isi minimal satu detail pekerjaan."),
        site_id: z.string(), // "" = ikut lokasi rencana
        work_type_id: z.string(), // "" = ikut jenis rencana
        member_mode: z.enum(["all", "custom"]), // all = seluruh tim; custom = hanya yang dipilih (ketua selalu ikut)
        member_ids: z.array(z.string()),
      }),
    ),
    holidays: z.array(z.string()), // tanggal dalam rentang yang diliburkan (dikeluarkan dari rencana)
    tool_ids: z.array(z.string()),
    vehicle_id: z.string(),
    leader_employee_id: required("Pilih ketua tim."),
    member_employee_ids: z.array(z.string()),
    driver_employee_id: z.string(),
    is_out_of_town: z.boolean(),
    work_type_id: z.string(),
    one_day: z.boolean(),
  })
  .refine((v) => v.period_end >= v.period_start, {
    path: ["period_end"],
    message: "Tanggal selesai tidak boleh sebelum tanggal mulai.",
  })
  .refine((v) => !v.vehicle_id || v.driver_employee_id.length > 0, { path: ["driver_employee_id"], message: "Pilih driver kendaraan." });
export type Values = z.infer<typeof planEditorSchema>;
export type TaskValue = Values["days"][number]["tasks"][number];
