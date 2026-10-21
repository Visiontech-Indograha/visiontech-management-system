import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
/** Jadwal harian daily-first (Milestone 5): minggu = rentang tanggal; DRAFT → SUBMITTED → APPROVED → ONGOING → COMPLETED. */
export type DailyPlan = S["DailyPlanOut"];
export type DailyPlanDetail = S["DailyPlanDetail"];
export type DailyPlanCreate = S["DailyPlanCreate"];
export type DailyPlanUpdate = S["DailyPlanUpdate"];
export type DailyFormOptions = S["DailyFormOptions"];
export type GeoResult = S["GeoResult"];
export type DailyAction = "submit" | "approve" | "start" | "complete";

const KEY = ["daily-plans"] as const;

/** Tanggal ISO (YYYY-MM-DD) menurut WIB. */
export const wibDate = (d: Date = new Date()) => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(d);

/** Senin minggu yang memuat tanggal ISO ini. */
export function weekStart(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export interface DailyFilters {
  start: string;
  end: string;
  division_id?: string;
}

export const useDailyPlans = (f: DailyFilters) =>
  useQuery({
    queryKey: [...KEY, "list", f],
    queryFn: async () =>
      (await api.get<DailyPlan[]>("/work-plans/daily", {
        params: { start: f.start, end: f.end, ...(f.division_id ? { division_id: f.division_id } : {}) },
      })).data,
  });

export const useDailyPlan = (id: string | null) =>
  useQuery({
    queryKey: [...KEY, "detail", id],
    enabled: !!id,
    queryFn: async () => (await api.get<DailyPlanDetail>(`/work-plans/daily/${id}`)).data,
  });

export const useDailyFormOptions = (enabled: boolean) =>
  useQuery({
    queryKey: [...KEY, "options"],
    enabled,
    staleTime: 60_000,
    queryFn: async () => (await api.get<DailyFormOptions>("/work-plans/form-options")).data,
  });

function useDailyMutation<V, D>(fn: (v: V) => Promise<D>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
}

export const useCreateDailyPlan = () =>
  useDailyMutation(async (body: DailyPlanCreate) => (await api.post<DailyPlan>("/work-plans/daily", body)).data);

export const useUpdateDailyPlan = (id: string) =>
  useDailyMutation(async (body: DailyPlanUpdate) => (await api.put<DailyPlan>(`/work-plans/daily/${id}`, body)).data);

export const useDeleteDailyPlan = () =>
  useDailyMutation(async (id: string) => (await api.delete(`/work-plans/daily/${id}`)).data);

export const useDailyTransition = () =>
  useDailyMutation(async ({ id, action }: { id: string; action: DailyAction }) =>
    (await api.post<DailyPlan>(`/work-plans/daily/${id}/${action}`)).data);

export const useRejectDailyPlan = () =>
  useDailyMutation(async ({ id, reason }: { id: string; reason: string }) =>
    (await api.post<DailyPlan>(`/work-plans/daily/${id}/reject`, { reason })).data);

export const useCopyDailyPlan = () =>
  useDailyMutation(async ({ id, work_dates }: { id: string; work_dates: string[] }) =>
    (await api.post<DailyPlan[]>(`/work-plans/daily/${id}/copy`, { work_dates })).data);

/** Persetujuan matriks: setujui banyak jadwal sekaligus (yang tidak memenuhi syarat dilewati API). */
export const useBulkApprove = () =>
  useDailyMutation(async (daily_plan_ids: string[]) =>
    (await api.post<S["BulkApproveOut"]>("/work-plans/daily/approve", { daily_plan_ids })).data);

export const geoSearch = async (q: string) => (await api.get<GeoResult[]>("/work-plans/geo/search", { params: { q } })).data;

// ── Item per titik (Milestone 6) ─────────────────────────────────────────────
export type PlanItem = S["PlanItemOut"];
export type PlanItemCreate = S["PlanItemCreate"];
export type RolloverDecision = S["RolloverDecision"];

export const useCreatePlanItem = (dailyPlanId: string) =>
  useDailyMutation(async (body: PlanItemCreate) =>
    (await api.post<PlanItem>(`/work-plans/daily/${dailyPlanId}/items`, body)).data);

export const useDeletePlanItem = () =>
  useDailyMutation(async (itemId: string) => (await api.delete(`/work-plans/items/${itemId}`)).data);

/** PM/OM: setujui geser (ke jadwal yang ada / tanggal baru) atau tolak. */
export const useDecideRollover = () =>
  useDailyMutation(async ({ itemId, ...body }: RolloverDecision & { itemId: string }) =>
    (await api.post<PlanItem>(`/work-plans/items/${itemId}/rollover-decision`, body)).data);
