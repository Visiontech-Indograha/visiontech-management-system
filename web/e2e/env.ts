/** Konfigurasi E2E dari env. Tidak pernah menunjuk lingkungan produksi. */
export const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

const host = new URL(BASE_URL).hostname;
const lokal = /^(localhost|127\.0\.0\.1|\[::1\]|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)$/.test(host);
if (!lokal) {
  throw new Error(`E2E hanya boleh menyasar lingkungan lokal (dapat: ${host}). Tidak dijalankan.`);
}

export const API_URL = process.env.E2E_API_URL ?? `${BASE_URL}/api/v1`;

export type Akun = { email: string; password: string };
export type Peran = "ADMIN" | "STAFF";

/** Kredensial dari env: E2E_<PERAN>_EMAIL dan E2E_<PERAN>_PASSWORD. Tidak pernah di-commit. */
export function akun(peran: Peran): Akun | null {
  const email = process.env[`E2E_${peran}_EMAIL`];
  const password = process.env[`E2E_${peran}_PASSWORD`];
  return email && password ? { email, password } : null;
}

/** Awalan data uji; semua data buatan tes memakai ini dan dihapus tes itu sendiri. */
export const PREFIX = "QA-E2E-";
