import { z } from "zod";

/** Email login akun karyawan (server tetap memeriksa ulang: format, panjang 254, dan keunikan). */
export const accountLoginSchema = z.object({
  login: z
    .string()
    .trim()
    .min(1, "Email wajib diisi.")
    .max(254, "Email terlalu panjang (maksimal 254 karakter).")
    .email("Format email tidak valid."),
});
export type AccountLoginValues = z.infer<typeof accountLoginSchema>;
