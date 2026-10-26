import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Overtime = components["schemas"]["OvertimeResponse"];

/** GET /overtime?work_plan_id= — lembur yang diajukan dalam satu rencana kerja. */
export async function listPlanOvertime(planId: string): Promise<Overtime[]> {
  return (await api.get<Overtime[]>("/overtime", { params: { daily_plan_id: planId, work_plan_id: planId } })).data;
}

/** POST /overtime — ajukan lembur (tanggal dicatat server). */
export async function createOvertime(body: components["schemas"]["OvertimeCreate"]): Promise<Overtime> {
  return (await api.post<Overtime>("/overtime", body)).data;
}

/** POST /overtime/{id}/review — PM menyetujui/menolak lembur. */
export async function reviewOvertime(id: string, body: components["schemas"]["OvertimeReview"]): Promise<Overtime> {
  return (await api.post<Overtime>(`/overtime/${id}/review`, body)).data;
}

const overtimeKey = (planId: string) => ["overtime", planId] as const;

/** Daftar lembur satu rencana kerja (TanStack Query). */
export const useOvertime = (planId: string) =>
  useQuery({
    queryKey: overtimeKey(planId),
    queryFn: () => listPlanOvertime(planId),
  });

/** Mutasi lembur yang menyegarkan daftar lembur rencana & rekap lembur. */
export function useOvertimeMutation<V>(planId: string, fn: (v: V) => Promise<Overtime>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: overtimeKey(planId) });
      await qc.invalidateQueries({ queryKey: ["overtime-recap"] });
    },
  });
}
