import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type PlanLocation = components["schemas"]["PlanLocationOut"];
export type PlanLocationIn = components["schemas"]["PlanLocationIn"];

/** GET /work-plans/{id}/location — titik & radius lokasi rencana (null bila belum ada). */
export async function getPlanLocation(planId: string): Promise<PlanLocation | null> {
  return (await api.get<PlanLocation | null>(`/work-plans/${planId}/location`)).data;
}

/** PUT /work-plans/{id}/location — simpan titik lokasi rencana. */
export async function savePlanLocation(planId: string, body: PlanLocationIn): Promise<PlanLocation> {
  return (await api.put<PlanLocation>(`/work-plans/${planId}/location`, body)).data;
}

/** Kunci cache lokasi rencana kerja. */
export const planLocationKey = (planId: string) => ["plan-location", planId] as const;

/** Lokasi rencana kerja (TanStack Query). */
export function usePlanLocation(planId: string) {
  return useQuery({
    queryKey: planLocationKey(planId),
    queryFn: () => getPlanLocation(planId),
  });
}
