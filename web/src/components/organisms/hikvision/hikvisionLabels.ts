import { formatDateTime } from "@/lib/format";
import type { Perangkat } from "@/services/hikvisionService";

export const MODE_LABEL: Record<Perangkat["mode"], string> = {
  SHADOW: "Bayangan",
  AKTIF: "Aktif",
};

export const MODE_HINT: Record<Perangkat["mode"], string> = {
  SHADOW: "Hanya mencatat. Belum dipakai untuk absensi.",
  AKTIF: "Dipakai untuk absensi karyawan.",
};

export const formatWhen = (iso: string | null) => (iso ? formatDateTime(iso) : "Belum ada");
