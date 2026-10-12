import { api } from "@/lib/apiClient";
import type { Me, TokenOut } from "@/lib/types";

/**
 * Operasi akun yang tidak lewat TanStack Query. Galat diteruskan sebagai `ApiError` (lib/apiClient) —
 * pemanggil memetakan `details.fields` ke field form.
 */

/** POST /auth/change-password → token baru (sesi lama dicabut server). */
export async function changePassword(current_password: string, new_password: string): Promise<TokenOut> {
  const { data } = await api.post<TokenOut>("/auth/change-password", { current_password, new_password });
  return data;
}

/** POST /auth/login (platform web) → token akses. Galat 401/423 diteruskan sebagai `ApiError`. */
export async function login(email: string, password: string): Promise<TokenOut> {
  return (await api.post<TokenOut>("/auth/login", { email, password, platform: "web" })).data;
}

/** POST /auth/logout — cabut sesi refresh di server. */
export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

/** GET /auth/me — profil, peran, dan izin pengguna aktif. */
export async function fetchMe(): Promise<Me> {
  return (await api.get<Me>("/auth/me")).data;
}
