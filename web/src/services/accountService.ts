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

export interface FaceStatus {
  employee_linked: boolean;
  consent: "GRANTED" | "WITHDRAWN" | null;
  consent_policy_version?: string | null;
  enrolled: boolean;
  enrollment_version?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  liveness_required: boolean;
  enrollment_required?: boolean;
  template_ttl_days: number;
  policy: {
    version: string;
    text: string;
  };
}

export function useFaceStatus() {
  return useQuery({
    queryKey: ["face", "status"],
    queryFn: async () => (await api.get<FaceStatus>("/face/status")).data,
  });
}

export function useSetFaceConsent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ state, policy_version }: { state: "GRANTED" | "WITHDRAWN"; policy_version: string }) =>
      (await api.post<{ message: string }>("/face/consent", { state, policy_version })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["face", "status"] }),
  });
}
