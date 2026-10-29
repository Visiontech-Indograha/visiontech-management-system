const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

/** Format tanggal-jam WIB: "21 Sep 2026 07.42 WIB" (docs/06-UI-UX §6). */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Jakarta",
    day: "numeric",
    month: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("day")} ${MONTHS[Number(get("month")) - 1]} ${get("year")} ${get("hour")}.${get("minute")} WIB`;
}

/** Jam WIB saja: "07.42". */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Jakarta",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("hour")}.${get("minute")}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** Jarak dalam meter → "711 m" atau "463,8 km" bila ≥ 1 km. */
export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined || Number.isNaN(meters)) return "-";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} km`;
}

const FACE_RESULT_LABEL: Record<string, string> = {
  MATCH: "Cocok",
  NO_MATCH: "Tidak cocok",
  MISMATCH: "Tidak cocok",
  SKIPPED: "Tidak diperiksa",
  NOT_ENROLLED: "Wajah belum terdaftar",
  LOW_QUALITY: "Foto kurang jelas",
};

export function faceResultLabel(result: string | null | undefined): string {
  if (!result) return "-";
  return FACE_RESULT_LABEL[result] ?? result;
}
