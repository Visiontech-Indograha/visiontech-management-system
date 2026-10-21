import { z } from "zod";

/** Validasi form jenis pekerjaan + template foto laporan (label slot unik). */
export const workTypeSchema = z.object({
  name: z.string().trim().min(1, "Nama jenis pekerjaan wajib diisi."),
  division_id: z.string().trim().optional().nullable(),
  description: z.string().trim().optional().nullable(),
  kind: z.enum(["WORK", "SURVEY_TASK", "SURVEY_POINT"]),
  follow_up_work_type_id: z.string().nullable(),
  photos: z
    .array(
      z.object({
        label: z.string().trim().min(1, "Label slot wajib diisi."),
        hint: z.string().trim(),
        required: z.boolean(),
        example_file_id: z.string().nullable(),
      }),
    )
    .refine((slots) => new Set(slots.map((s) => s.label.trim().toLowerCase())).size === slots.length, {
      message: "Label slot tidak boleh kembar.",
    }),
});
export type WorkTypeValues = z.infer<typeof workTypeSchema>;
