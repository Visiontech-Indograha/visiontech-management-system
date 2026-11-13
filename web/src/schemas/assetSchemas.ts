import { z } from "zod";

/** Validasi form aset V2: tambah alat/kendaraan, (serah terima & berkas divalidasi di dialognya). */
const required = (label: string) => z.string().trim().min(1, `${label} wajib diisi.`);

export const toolSchema = z.object({
  office_id: required("Kantor"),
  division_id: z.string(),
  ownership_type: z.enum(["PERSONAL_LOAN", "SHARED_TOOL"]),
  category: z.enum(["BAJU", "LAPTOP", "SEPATU", "BOR", "TANGGA", "LAINNYA"]),
  name: z.string().trim().min(2, "Nama alat minimal 2 karakter.").max(100, "Nama alat maksimal 100 karakter."),
  tool_code: z.string().trim().min(2, "Kode alat minimal 2 karakter.").max(50, "Kode alat maksimal 50 karakter."),
});
export type ToolValues = z.infer<typeof toolSchema>;

export const vehicleSchema = z.object({
  office_id: required("Kantor"),
  division_id: required("Divisi"),
  vehicle_type: z.enum(["Motorcycle", "Car", "Truck"]),
  name: z.string().trim().min(2, "Nama kendaraan minimal 2 karakter.").max(150, "Nama kendaraan maksimal 150 karakter."),
  number_plate: z.string().trim().min(3, "Nomor polisi wajib diisi.").max(20, "Nomor polisi maksimal 20 karakter."),
});
export type VehicleValues = z.infer<typeof vehicleSchema>;

/** Penerima eksternal: batas sama dengan BorrowerCreate di API (nama 1-150, instansi 150, kontak 100). */
export const borrowerSchema = z.object({
  office_id: required("Kantor"),
  nama: z.string().trim().min(1, "Nama penerima wajib diisi.").max(150, "Nama penerima maksimal 150 karakter."),
  instansi: z.string().trim().max(150, "Instansi maksimal 150 karakter."),
  kontak: z.string().trim().max(100, "Kontak maksimal 100 karakter."),
});
export type BorrowerValues = z.infer<typeof borrowerSchema>;
