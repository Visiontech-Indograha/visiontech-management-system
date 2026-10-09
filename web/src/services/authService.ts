import { api } from "@/lib/apiClient";
import type { TokenOut } from "@/lib/types";

/**
 * Operasi akun yang tidak lewat TanStack Query. Galat diteruskan sebagai `ApiError` (lib/apiClient) —
 * pemanggil memetakan `details.fields` ke field form.
 */

/** POST /auth/change-password → token baru (sesi lama dicabut server). */
export async function changePassword(current_password: string, new_password: string): Promise<TokenOut> {
  const { data } = await api.post<TokenOut>("/auth/change-password", { current_password, new_password });
  return data;
}
