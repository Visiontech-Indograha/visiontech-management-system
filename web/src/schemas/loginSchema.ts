import { z } from "zod";

/** Validasi form login (server tetap memeriksa ulang). */
export const loginSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Email wajib diisi.")
    .max(254, "Email terlalu panjang (maksimal 254 karakter).")
    .email("Format email tidak valid."),
  password: z.string().min(1, "Sandi wajib diisi."),
});
export type LoginValues = z.infer<typeof loginSchema>;
