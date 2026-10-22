import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type ActiveSession = components["schemas"]["AuthSessionResponseSchema"];
type RevokeOthers = components["schemas"]["AuthRevokeOthersResponseSchema"];

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

/** GET /face/status (wajah V2). `required`: pekerja lapangan wajib mendaftar sebelum memakai aplikasi. */
export interface FaceStatus {
  enrolled: boolean;
  enrolled_at?: string | null;
  model_name?: string | null;
  required: boolean;
}

export function useFaceStatus() {
  return useQuery({
    queryKey: ["face", "status"],
    queryFn: async () => (await api.get<FaceStatus>("/face/status")).data,
  });
}
