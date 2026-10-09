import { z } from "zod";

/** Validasi form ganti password (server tetap memeriksa ulang). */
export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Password saat ini wajib diisi."),
    new_password: z
      .string()
      .min(8, "Password minimal 8 karakter.")
      .regex(/[A-Za-z]/, "Password harus memuat huruf.")
      .regex(/\d/, "Password harus memuat angka."),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    path: ["confirm"],
    message: "Konfirmasi password tidak sama.",
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
