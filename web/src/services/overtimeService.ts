import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

/** GET /overtime?status=PENDING_PM — lembur yang menunggu keputusan (API memfilter sesuai hak peninjau). */
export async function listPendingOvertime(): Promise<Overtime[]> {
  return (await api.get<Overtime[]>("/overtime", { params: { status: "PENDING_PM" } })).data;
}

const overtimeKey = (planId: string) => ["overtime", planId] as const;

/** Antrean tinjau lembur. Prefix ["overtime"] ikut tersegarkan saat ada keputusan. */
export const useOvertimePending = () =>
  useQuery({
    queryKey: ["overtime", "pending"],
    queryFn: listPendingOvertime,
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

/** Lembur milik sendiri (API memfilter menurut akun: karyawan hanya miliknya). */
export const useMyOvertime = (employeeId?: string | null) =>
  useQuery({
    queryKey: ["overtime", "mine"],
    queryFn: async () => (await api.get<Overtime[]>("/overtime")).data,
    // Peninjau menerima lembur banyak orang dari API; daftar ini hanya milik pengguna login.
    select: (rows) => rows.filter((r) => r.employee_id === employeeId),
  });

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
