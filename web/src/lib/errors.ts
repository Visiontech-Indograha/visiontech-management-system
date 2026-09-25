import { ApiError } from "./api";

/** Pesan galat untuk pengguna: pesan Indonesia dari API bila ada, selain itu pesan umum. */
export function errorMessage(err: unknown, fallback = "Terjadi kesalahan. Coba lagi."): string {
  return err instanceof ApiError ? err.message : fallback;
}
