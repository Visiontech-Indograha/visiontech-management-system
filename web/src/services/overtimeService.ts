import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Overtime = components["schemas"]["OvertimeResponse"];

/** GET /overtime?work_plan_id= — lembur yang diajukan dalam satu rencana kerja. */
export async function listPlanOvertime(planId: string): Promise<Overtime[]> {
  return (await api.get<Overtime[]>("/overtime", { params: { work_plan_id: planId } })).data;
}

/** POST /overtime — ajukan lembur (tanggal dicatat server). */
export async function createOvertime(body: components["schemas"]["OvertimeCreate"]): Promise<Overtime> {
  return (await api.post<Overtime>("/overtime", body)).data;
}

/** POST /overtime/{id}/review — PM menyetujui/menolak lembur. */
export async function reviewOvertime(id: string, body: components["schemas"]["OvertimeReview"]): Promise<Overtime> {
  return (await api.post<Overtime>(`/overtime/${id}/review`, body)).data;
}
