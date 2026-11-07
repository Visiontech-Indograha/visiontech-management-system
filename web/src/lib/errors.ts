import { ApiError } from "./apiClient";

/** Pesan galat untuk pengguna: pesan Indonesia dari API bila ada, selain itu pesan umum. */
export function errorMessage(err: unknown, fallback = "Terjadi kesalahan. Coba lagi."): string {
  if (err instanceof ApiError && err.code === "IDEMPOTENCY_SEDANG_DIPROSES") {
    return "Pengajuan sedang diproses, tunggu sebentar.";
  }
  return err instanceof ApiError ? err.message : fallback;
}

export const GENERIC_FIELD_ERROR = "Isian tidak valid. Periksa panjang atau format.";

/** Pesan galat pydantic (Inggris) menjadi Bahasa Indonesia awam; tanpa pola cocok, pesan umum. */
export function translateFieldMessage(raw: unknown): string {
  const m = typeof raw === "string" ? raw.trim() : "";
  if (!m) return GENERIC_FIELD_ERROR;
  let r: RegExpMatchArray | null;
  if ((r = m.match(/at most (\d+) (character|item)/i))) return r[2].toLowerCase() === "item" ? `Maksimal ${r[1]} pilihan.` : `Maksimal ${r[1]} karakter.`;
  if ((r = m.match(/at least (\d+) (character|item)/i))) return r[2].toLowerCase() === "item" ? `Pilih minimal ${r[1]}.` : `Minimal ${r[1]} karakter.`;
  if (/field required|^missing$|should not be null/i.test(m)) return "Isian ini wajib diisi.";
  if (/should match pattern|string_pattern_mismatch/i.test(m)) return "Format isian belum sesuai.";
  if ((r = m.match(/greater than or equal to (-?[\d.]+)/i))) return `Nilai minimal ${r[1]}.`;
  if ((r = m.match(/greater than (-?[\d.]+)/i))) return `Nilai harus lebih besar dari ${r[1]}.`;
  if ((r = m.match(/less than or equal to (-?[\d.]+)/i))) return `Nilai maksimal ${r[1]}.`;
  if ((r = m.match(/less than (-?[\d.]+)/i))) return `Nilai harus lebih kecil dari ${r[1]}.`;
  if (/valid (integer|number)|unable to parse string as an? (integer|number)/i.test(m)) return "Isi dengan angka yang benar.";
  if (/valid (email|date|datetime|uuid)/i.test(m)) return "Format isian belum sesuai.";
  if (/\b(should|must|string|input|value|field|error)\b/i.test(m)) return GENERIC_FIELD_ERROR;
  return m;
}

/**
 * Galat 422 dari API (`details.fields`: lokasi → pesan) dipetakan ke kolom formulir; true bila ada yang dipetakan.
 * Pesan pydantic berbahasa Inggris, jadi kolom diberi pesan Indonesia yang seragam.
 */
export function applyFieldErrors(
  err: unknown,
  setError: (name: never, error: { type: string; message: string }) => void,
  known?: readonly string[],
): boolean {
  if (!(err instanceof ApiError) || err.status !== 422) return false;
  const fields = err.details.fields;
  if (!fields || typeof fields !== "object") return false;
  let applied = false;
  for (const name of Object.keys(fields)) {
    if (known && !known.includes(name)) continue;
    setError(name as never, { type: "server", message: translateFieldMessage((fields as Record<string, unknown>)[name]) });
    applied = true;
  }
  return applied;
}
