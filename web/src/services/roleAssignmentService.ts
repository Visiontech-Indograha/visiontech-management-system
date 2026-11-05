import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { idempotencyHeaders } from "@/lib/idempotency";
import type { components } from "@/lib/apiTypes";

export type RoleAssignment = components["schemas"]["RoleAssignmentOut"];
export type RoleAssignmentCreate = components["schemas"]["RoleAssignmentCreate"];

const keyOf = (userId: string) => ["role-assignments", userId] as const;

/** GET /users/{id}/role-assignments — penugasan aktif (hanya pemegang manage:role_assignments). */
export const useRoleAssignments = (userId: string | null | undefined) =>
  useQuery({
    queryKey: keyOf(userId ?? ""),
    enabled: !!userId,
    queryFn: async () => (await api.get<RoleAssignment[]>(`/users/${userId}/role-assignments`)).data,
  });

/** POST /users/{id}/role-assignments — tambah peran; Idempotency-Key mencegah penugasan ganda. */
export function useAddRoleAssignment(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ body, key }: { body: RoleAssignmentCreate; key?: string }) =>
      (await api.post<RoleAssignment>(`/users/${userId}/role-assignments`, body, { headers: idempotencyHeaders(key) })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: keyOf(userId) }),
  });
}

/** DELETE /users/{id}/role-assignments/{assignmentId} — cabut peran tambahan. */
export function useRevokeRoleAssignment(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assignmentId: string) => {
      await api.delete(`/users/${userId}/role-assignments/${assignmentId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: keyOf(userId) }),
  });
}
