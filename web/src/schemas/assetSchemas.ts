import { z } from "zod";

/** Validasi form aset V2: tambah alat/kendaraan, (serah terima & berkas divalidasi di dialognya). */
const required = (label: string) => z.string().trim().min(1, `${label} wajib diisi.`);

export const toolSchema = z.object({
  office_id: required("Kantor"),
  division_id: z.string(),
  ownership_type: z.enum(["PERSONAL_LOAN", "SHARED_TOOL"]),
  category: z.enum(["BAJU", "LAPTOP", "SEPATU", "BOR", "TANGGA", "LAINNYA"]),
  name: z.string().trim().min(2, "Nama alat minimal 2 karakter."),
  tool_code: z.string().trim().min(2, "Kode alat minimal 2 karakter."),
});
export type ToolValues = z.infer<typeof toolSchema>;

export const vehicleSchema = z.object({
  office_id: required("Kantor"),
  division_id: required("Divisi"),
  vehicle_type: z.enum(["Motorcycle", "Car", "Truck"]),
  name: z.string().trim().min(2, "Nama kendaraan minimal 2 karakter."),
  number_plate: z.string().trim().min(3, "Nomor polisi wajib diisi."),
});
export type VehicleValues = z.infer<typeof vehicleSchema>;
