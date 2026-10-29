import { ApiError } from "./apiClient";

/** Pesan galat untuk pengguna: pesan Indonesia dari API bila ada, selain itu pesan umum. */
export function errorMessage(err: unknown, fallback = "Terjadi kesalahan. Coba lagi."): string {
  return err instanceof ApiError ? err.message : fallback;
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
    setError(name as never, { type: "server", message: "Isian tidak valid. Periksa panjang atau format." });
    applied = true;
  }
  return applied;
}
