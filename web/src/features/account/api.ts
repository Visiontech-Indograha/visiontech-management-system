import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type ActiveSession = components["schemas"]["SessionOut"];
type RevokeOthers = components["schemas"]["RevokeOthersResponse"];

const key = ["auth", "sessions"] as const;

/** P1-7: perangkat yang sedang masuk dengan akun ini (GET /auth/sessions). */
export const useSessions = () =>
  useQuery({ queryKey: key, queryFn: async () => (await api.get<ActiveSession[]>("/auth/sessions")).data });

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.post(`/auth/sessions/${id}/revoke`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export function useRevokeOtherSessions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<RevokeOthers>("/auth/sessions/revoke-others")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}
