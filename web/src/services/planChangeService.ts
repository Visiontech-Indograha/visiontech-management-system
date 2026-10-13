import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Change = components["schemas"]["PlanChangeOut"];
export const changesKey = (planId: string) => ["plan-changes", planId] as const;

/** Usulan perubahan (permintaan revisi, perpanjangan, personel) sebuah rencana kerja. */
export function usePlanChanges(planId: string) {
  return useQuery({
    queryKey: changesKey(planId),
    queryFn: async () => (await api.get<Change[]>(`/work-plans/${planId}/changes`)).data,
  });
}

export type ChangeResponse = components["schemas"]["ChangeResponse"];
export type ChangeRequest = components["schemas"]["ChangeRequest"];

/** POST /work-plans/{id}/changes — ajukan perubahan personel / perpanjangan. */
export async function requestPlanChange(planId: string, body: ChangeRequest): Promise<ChangeResponse> {
  return (await api.post<ChangeResponse>(`/work-plans/${planId}/changes`, body)).data;
}

/** POST /changes/{id}/{action} — putuskan perubahan (approve/accept/reject/withdraw). */
export async function decidePlanChange(changeId: string | undefined, action: string, reason?: string): Promise<ChangeResponse> {
  return (await api.post<ChangeResponse>(`/changes/${changeId}/${action}`, { reason: reason ?? null })).data;
}
