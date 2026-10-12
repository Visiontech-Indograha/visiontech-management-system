import { NAV_ITEMS } from "./navigation";

export const APP_NAME = "Visiontech VMS";
export const DEFAULT_TITLE = `${APP_NAME} — Manajemen Pekerjaan Lapangan`;

/** Pola rute (urut dari yang paling spesifik) → judul halaman. Menu utama diambil dari NAV_ITEMS. */
const PATTERNS: [RegExp, string][] = [
  [/^\/login$/, "Masuk"],
  [/^\/admin-login$/, "Masuk administrator"],
  [/^\/verify(\/.*)?$/, "Verifikasi dokumen"],
  [/^\/change-password$/, "Ganti password"],
  [/^\/account$/, "Akun & keamanan"],
  [/^\/forbidden$/, "Tidak berwenang"],
  [/^\/work-plans\/new$/, "Buat rencana kerja"],
  [/^\/work-plans\/[^/]+\/edit$/, "Sunting rencana kerja"],
  [/^\/work-plans\/[^/]+\/amend\/[^/]+$/, "Revisi rencana kerja"],
  [/^\/work-plans\/[^/]+\/presentation$/, "Presentasi laporan"],
  [/^\/work-plans\/[^/]+$/, "Detail rencana kerja"],
  [/^\/directory\/[^/]+$/, "Detail karyawan"],
];

/** Judul tab peramban untuk satu alamat; `null` bila tidak dikenal (dipakai sebagai "halaman tidak ditemukan"). */
export function pageTitle(pathname: string): string {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  for (const [re, label] of PATTERNS) if (re.test(path)) return `${label} · ${APP_NAME}`;
  const item = NAV_ITEMS.find((i) => i.path === path);
  if (item) return `${item.label} · ${APP_NAME}`;
  return `Halaman tidak ditemukan · ${APP_NAME}`;
}
