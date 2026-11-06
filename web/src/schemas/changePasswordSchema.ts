import { z } from "zod";

/** Validasi form ganti sandi (server tetap memeriksa ulang). */
export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Sandi saat ini wajib diisi."),
    new_password: z
      .string()
      .min(8, "Sandi minimal 8 karakter.")
      .regex(/[A-Za-z]/, "Sandi harus memuat huruf.")
      .regex(/\d/, "Sandi harus memuat angka."),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    path: ["confirm"],
    message: "Konfirmasi sandi tidak sama.",
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
