import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type VerifyOut = components["schemas"]["VerifyOut"];

/** GET /verify/{token} — PUBLIK (tanpa login). Tidak diulang otomatis: token salah tetap salah. */
export function useVerification(token: string) {
  return useQuery({
    queryKey: ["verify", token],
    queryFn: async () => (await api.get<VerifyOut>(`/verify/${token}`)).data,
    enabled: !!token,
    retry: false,
  });
}
