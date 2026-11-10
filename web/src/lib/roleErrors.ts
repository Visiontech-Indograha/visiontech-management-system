import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";

const PESAN_PERAN: Record<string, string> = {
  ROLE_SELF_CHANGE: "Anda tidak bisa mengubah peran akun Anda sendiri.",
  ROLE_PROTECTED: "Peran Super Admin tidak bisa diubah dari sini.",
  ROLE_NOT_ASSIGNABLE: "Peran itu tidak bisa dipilih untuk akun ini.",
};

/** Pesan awam untuk galat ubah peran (409/422); selain itu pakai pesan server. */
export function pesanGalatPeran(err: unknown): string {
  const code = err instanceof ApiError ? err.code : "";
  if (PESAN_PERAN[code]) return PESAN_PERAN[code];
  if (err instanceof ApiError && err.status === 422) return "Peran yang dipilih tidak valid. Pilih peran lain.";
  return errorMessage(err, "Peran belum bisa diubah. Coba lagi.");
}
