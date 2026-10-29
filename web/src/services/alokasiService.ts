import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import type { BulkOut, PlanItemInput, WeeklyMatrix } from "@/lib/alokasi";

type S = components["schemas"];
export type OrderSchedule = S["OrderScheduleOut"];
export type DailyPlanOut = S["DailyPlanOut"];

const KEY = ["alokasi-mingguan"] as const;

/** Matriks tim × hari Senin–Minggu untuk divisi yang dikelola PM/OM (divisionId kosong = semua divisi). */
export const useWeeklyMatrix = (weekStart: string, divisionId: string) =>
  useQuery({
    queryKey: [...KEY, "weekly", weekStart, divisionId],
    queryFn: async () =>
      (await api.get<WeeklyMatrix>("/work-plans/weekly", {
        params: { week_start: weekStart, ...(divisionId ? { division_id: divisionId } : {}) },
      })).data,
  });

/** Sisa target satu order: total, selesai, dan yang belum dijadwalkan (untuk dialog Alokasikan). */
export const useOrderSchedule = (completionId: string) =>
  useQuery({
    queryKey: [...KEY, "order", completionId],
    enabled: !!completionId,
    queryFn: async () => (await api.get<OrderSchedule>(`/work-plans/orders/${completionId}/schedule`)).data,
  });

function useInvalidatingMutation<V, D>(fn: (v: V) => Promise<D>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: KEY });
      void qc.invalidateQueries({ queryKey: ["daily-plans"] });
    },
  });
}

export const useBulkAllocate = () =>
  useInvalidatingMutation(async (body: {
    division_id: string;
    team_ids: string[];
    work_dates: string[];
  }) => (await api.post<BulkOut>("/work-plans/daily/bulk", { ...body, kind: "WORK", target: "DRAFT" })).data);

export const useBulkStandby = () =>
  useInvalidatingMutation(async (body: { division_id: string; team_ids: string[]; work_dates: string[] }) =>
    (await api.post<BulkOut>("/work-plans/daily/bulk-standby", body)).data);

/** Tambah pekerjaan ke jadwal yang baru dibuat (berurutan; satu galat tidak membatalkan yang lain). */
export async function addItemToPlan(dailyPlanId: string, item: PlanItemInput) {
  return (await api.post(`/work-plans/daily/${dailyPlanId}/items`, item)).data;
}

export const useActivateStandby = () =>
  useInvalidatingMutation(async ({ id, items }: { id: string; items: PlanItemInput[] }) =>
    (await api.post<DailyPlanOut>(`/work-plans/daily/${id}/activate`, { items })).data);

export const useCopyPlan = () =>
  useInvalidatingMutation(async ({ id, work_dates }: { id: string; work_dates: string[] }) =>
    (await api.post<DailyPlanOut[]>(`/work-plans/daily/${id}/copy`, { work_dates })).data);
