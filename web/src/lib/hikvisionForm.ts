import type { DeviceValues } from "@/schemas/hikvisionSchemas";

const EMPTY: DeviceValues = { office_id: "", name: "", ip_address: "", http_port: "80", serial_no: "", model: "", catatan: "", aktif: "ya" };

interface DeviceLike {
  office_id: string; name: string; ip_address: string; http_port: number; serial_no: string;
  model: string | null; catatan: string | null; aktif: boolean;
}

export function deviceDefaults(d?: DeviceLike): DeviceValues {
  if (!d) return EMPTY;
  return {
    office_id: d.office_id, name: d.name, ip_address: d.ip_address, http_port: String(d.http_port), serial_no: d.serial_no,
    model: d.model ?? "", catatan: d.catatan ?? "", aktif: d.aktif ? "ya" : "tidak",
  };
}

/** Isian form -> badan permintaan. Mesin baru selalu mulai di mode Bayangan. */
export function deviceBody(v: DeviceValues) {
  return {
    name: v.name,
    ip_address: v.ip_address,
    http_port: Number(v.http_port),
    serial_no: v.serial_no,
    mode: "SHADOW" as const,
    model: v.model || null,
    catatan: v.catatan || null,
    aktif: v.aktif === "ya",
  };
}
