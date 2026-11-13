import { z } from "zod";

/** Batas sama dengan PerangkatBuat/PerangkatUbah di API (api hikvision). */
const ipv4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;
const ipv6 = /^[0-9a-fA-F:.]+$/;

export const isIpAddress = (v: string) => ipv4.test(v) || (v.includes(":") && ipv6.test(v));

export const deviceSchema = z.object({
  office_id: z.string().min(1, "Pilih kantor."),
  name: z.string().trim().min(1, "Nama mesin wajib diisi.").max(100, "Nama mesin maksimal 100 karakter."),
  ip_address: z
    .string()
    .trim()
    .min(3, "Alamat IP wajib diisi.")
    .max(45, "Alamat IP maksimal 45 karakter.")
    .refine(isIpAddress, { message: "Alamat IP tidak benar. Contoh: 192.168.1.20" }),
  http_port: z
    .string()
    .trim()
    .refine((v) => /^\d+$/.test(v) && Number(v) >= 1 && Number(v) <= 65535, { message: "Port harus angka 1 sampai 65535." }),
  serial_no: z
    .string()
    .trim()
    .min(1, "Nomor seri wajib diisi.")
    .max(64, "Nomor seri maksimal 64 karakter.")
    .regex(/^[A-Za-z0-9._-]+$/, "Nomor seri hanya huruf, angka, titik, garis bawah, atau tanda minus."),
  model: z.string().trim().max(64, "Model maksimal 64 karakter."),
  catatan: z.string().trim().max(500, "Catatan maksimal 500 karakter."),
  aktif: z.enum(["ya", "tidak"]),
});
export type DeviceValues = z.infer<typeof deviceSchema>;

export const mappingSchema = z.object({
  employee_no_string: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9._-]{1,50}$/, "Nomor di mesin 1 sampai 50 karakter: huruf, angka, titik, garis bawah, atau minus."),
  employee_id: z.string().min(1, "Pilih karyawan."),
});
export type MappingValues = z.infer<typeof mappingSchema>;
