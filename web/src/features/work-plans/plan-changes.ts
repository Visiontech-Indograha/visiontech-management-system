import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Change = components["schemas"]["PlanChangeOut"];
export const changesKey = (planId: string) => ["plan-changes", planId] as const;

/** Usulan perubahan (permintaan revisi, perpanjangan, personel) sebuah rencana kerja. */
export function usePlanChanges(planId: string) {
  return useQuery({
    queryKey: changesKey(planId),
    queryFn: async () => (await api.get<Change[]>(`/work-plans/${planId}/changes`)).data,
  });
}
