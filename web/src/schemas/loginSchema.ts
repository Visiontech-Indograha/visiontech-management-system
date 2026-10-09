import { z } from "zod";

/** Validasi form login (server tetap memeriksa ulang). */
export const loginSchema = z.object({
  email: z.string().trim().email("Format email tidak valid.").min(1, "Email wajib diisi."),
  password: z.string().min(1, "Password wajib diisi."),
});
export type LoginValues = z.infer<typeof loginSchema>;
