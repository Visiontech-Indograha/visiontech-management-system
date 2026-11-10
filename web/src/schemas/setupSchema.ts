import { z } from "zod";

/** Batas sama dengan skema API `SetupAdminIn` (api/app/modules/setup/schemas/setup_schema.py). */
export const setupSchema = z
  .object({
    setup_token: z.string().trim().min(1, "Kode penyiapan wajib diisi.").max(200, "Kode penyiapan terlalu panjang."),
    full_name: z
      .string()
      .trim()
      .min(2, "Nama lengkap minimal 2 huruf.")
      .max(150, "Nama terlalu panjang (maksimal 150 karakter)."),
    email: z
      .string()
      .trim()
      .min(5, "Email wajib diisi.")
      .max(254, "Email terlalu panjang (maksimal 254 karakter).")
      .regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, "Format email tidak valid."),
    password: z
      .string()
      .min(12, "Sandi minimal 12 karakter.")
      .max(128, "Sandi terlalu panjang (maksimal 128 karakter)."),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Konfirmasi sandi tidak sama." });
export type SetupValues = z.infer<typeof setupSchema>;
