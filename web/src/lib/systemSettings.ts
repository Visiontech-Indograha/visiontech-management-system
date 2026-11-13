import { ApiError } from "./apiClient";
import { errorMessage } from "./errors";

/** Asal nilai setelan dalam bahasa awam. */
export function settingSourceLabel(source: string): string {
  return source === "db" ? "Diubah di sini" : "Dari server";
}

export const SETTING_LOCKED_MESSAGE =
  "Setelan ini dikunci oleh pengaturan server, jadi tidak bisa diubah dari sini. Hubungi pengelola server bila perlu diubah.";

/** Pesan galat ubah setelan: 409 SETTING_LOCKED dijelaskan dengan bahasa awam. */
export function settingErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.code === "SETTING_LOCKED") return SETTING_LOCKED_MESSAGE;
  return errorMessage(err, "Setelan belum bisa diubah. Coba lagi.");
}
