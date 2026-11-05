import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useKeysetList } from "@/hooks/useKeysetList";
import { api } from "@/lib/apiClient";
import { idempotencyHeaders } from "@/lib/idempotency";
import type { components } from "@/lib/apiTypes";

export type Overtime = components["schemas"]["OvertimeResponse"];

/** GET /overtime?work_plan_id= — lembur yang diajukan dalam satu rencana kerja. */
export async function listPlanOvertime(planId: string): Promise<Overtime[]> {
  return (await api.get<Overtime[]>("/overtime", { params: { daily_plan_id: planId, work_plan_id: planId } })).data;
}

/** POST /overtime — ajukan lembur (tanggal dicatat server). */
export async function createOvertime(
  body: components["schemas"]["OvertimeCreate"],
  idempotencyKey?: string,
): Promise<Overtime> {
  return (await api.post<Overtime>("/overtime", body, { headers: idempotencyHeaders(idempotencyKey) })).data;
}

/** POST /overtime/{id}/review — PM menyetujui/menolak lembur. */
export async function reviewOvertime(id: string, body: components["schemas"]["OvertimeReview"]): Promise<Overtime> {
  return (await api.post<Overtime>(`/overtime/${id}/review`, body)).data;
}

const OT_SIZE = 20;

/** GET /overtime?status=PENDING_PM — antrean tinjau lembur (keyset; API memfilter sesuai hak peninjau). Prefix ["overtime"] ikut tersegarkan saat ada keputusan. */
export const useOvertimePending = () =>
  useKeysetList<Overtime[], Overtime[]>({
    key: ["overtime", "pending"],
    url: "/overtime",
    params: { status: "PENDING_PM", size: OT_SIZE },
    merge: (pages) => pages.flat(),
  });

/** Setujui/tolak lembur; menyegarkan antrean, daftar lembur rencana, dan rekap. */
export function useReviewOvertime() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision, note }: { id: string; decision: "APPROVED" | "REJECTED"; note?: string }) =>
      reviewOvertime(id, { decision, note }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["overtime"] });
      await qc.invalidateQueries({ queryKey: ["overtime-recap"] });
    },
  });
}

/** Lembur milik sendiri: server menyaring lewat `mine=true`, jadi satu muatan berisi baris pengguna dan "Muat lebih banyak" tepat. */
export const useMyOvertime = () =>
  useKeysetList<Overtime[], Overtime[]>({
    key: ["overtime", "mine"],
    url: "/overtime",
    params: { mine: true, size: OT_SIZE },
    merge: (pages) => pages.flat(),
  });

const overtimeKey = (planId: string) => ["overtime", planId] as const;

/** Ajukan lembur dengan kunci anti-ganda; menyegarkan semua daftar lembur. */
export function useCreateOvertime() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ body, key }: { body: components["schemas"]["OvertimeCreate"]; key?: string }) =>
      createOvertime(body, key),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["overtime"] });
      await qc.invalidateQueries({ queryKey: ["overtime-recap"] });
    },
  });
}

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
