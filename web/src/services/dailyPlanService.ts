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
export type RecentSite = S["RecentSiteOut"];
export type Correction = S["CorrectionOut"];
export type CorrectionDecision = S["CorrectionDecide"]["decision"];
export type DailyAction = "submit" | "approve" | "start" | "complete";

const KEY = ["daily-plans"] as const;

/** Jadwal tanggal lampau (PM/OM, beralasan) hanya boleh sampai sekian hari ke belakang; sama dengan API. */
export const BACKDATE_DAYS = 7;

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

/** Lokasi site yang pernah dipakai tim (untuk dipilih ulang di form); hanya diminta bila tim sudah dipilih. */
export const useRecentSites = (teamId: string) =>
  useQuery({
    queryKey: [...KEY, "recent-sites", teamId],
    enabled: !!teamId,
    staleTime: 60_000,
    queryFn: async () =>
      (await api.get<RecentSite[]>("/work-plans/daily/recent-sites", { params: { team_id: teamId, limit: 6 } })).data,
  });

function useDailyMutation<V, D>(fn: (v: V) => Promise<D>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
}

export const useCreateDailyPlan = () =>
  useDailyMutation(async (body: DailyPlanCreate) => (await api.post<DailyPlan>("/work-plans/daily", body)).data);

export const useUpdateDailyPlan = (id: string) =>
  useDailyMutation(async (body: DailyPlanUpdate) => (await api.put<DailyPlan>(`/work-plans/daily/${id}`, body)).data);

export type DailyPlanLocation = S["DailyPlanLocationUpdate"];

/** PATCH lokasi jadwal DISETUJUI yang belum dimulai (PM/OM); status tetap, tidak kembali ke draf. */
export const useUpdateDailyPlanLocation = (id: string) =>
  useDailyMutation(async (body: DailyPlanLocation) => (await api.patch<DailyPlan>(`/work-plans/daily/${id}/location`, body)).data);

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

/** Calon prasyarat item baru: item tim sendiri ≤ 30 hari terakhir + item tim lain di lokasi yang sama. */
export const usePrerequisiteOptions = (dailyPlanId: string) =>
  useQuery({
    queryKey: [...KEY, "prerequisite-options", dailyPlanId],
    queryFn: async () =>
      (await api.get<components["schemas"]["PrerequisiteOption"][]>(
        `/work-plans/daily/${dailyPlanId}/prerequisite-options`,
      )).data,
  });

export const useCreatePlanItem = (dailyPlanId: string) =>
  useDailyMutation(async (body: PlanItemCreate) =>
    (await api.post<PlanItem>(`/work-plans/daily/${dailyPlanId}/items`, body)).data);

/** Ringkasan target order: total, sudah dijadwalkan, dan sisa yang belum dijadwalkan (GET /work-plans/orders/{id}/schedule). */
export interface OrderScheduleSummary {
  total_target_unit: number;
  completed_target_unit: number;
  scheduled_target_qty: number;
  unscheduled_target_qty: number;
}

export const useOrderSchedule = (completionId: string) =>
  useQuery({
    queryKey: ["order-schedule", completionId],
    enabled: !!completionId,
    queryFn: async () =>
      (await api.get<OrderScheduleSummary>(`/work-plans/orders/${completionId}/schedule`)).data,
  });

export const useDeletePlanItem = () =>
  useDailyMutation(async (itemId: string) => (await api.delete(`/work-plans/items/${itemId}`)).data);

/** PM/OM: setujui geser (ke jadwal yang ada / tanggal baru) atau tolak. */
export const useDecideRollover = () =>
  useDailyMutation(async ({ itemId, ...body }: RolloverDecision & { itemId: string }) =>
    (await api.post<PlanItem>(`/work-plans/items/${itemId}/rollover-decision`, body)).data);

/** Item lengkap (foto realisasi, catatan, alasan geser) — bukti pekerjaan untuk PM. */
export const usePlanItem = (itemId: string) =>
  useQuery({
    queryKey: ["plan-item", itemId],
    queryFn: async () => (await api.get<components["schemas"]["PlanItemOut"]>(`/work-plans/items/${itemId}`)).data,
  });

export interface WeeklyPresentation {
  team_id: string;
  team_name: string;
  week_start: string;
  week_end: string;
  total_plans: number;
  completed_plans: number;
  daily_reports: Array<{
    report_id: string;
    daily_plan_id: string;
    leader_employee_id: string;
    leader_name?: string | null;
    summary: string;
    obstacles?: string | null;
    photos_json: unknown[];
    submitted_at: string;
    create_at: string;
  }>;
  presentation_notes?: string | null;
  pm_feedback?: string | null;
}

export async function getWeeklyPresentation(teamId: string, meetingDate: string): Promise<WeeklyPresentation> {
  return (await api.get<WeeklyPresentation>(`/work-plans/teams/${teamId}/weekly-presentation`, {
    params: { meeting_date: meetingDate },
  })).data;
}

export const useWeeklyPresentation = (teamId: string, meetingDate: string) =>
  useQuery({
    queryKey: ["weekly-presentation", teamId, meetingDate],
    queryFn: () => getWeeklyPresentation(teamId, meetingDate),
    enabled: Boolean(teamId && meetingDate),
  });

// ── Koreksi laporan harian ────────────────────────────────────────────────────
export const useCorrectionInbox = () =>
  useQuery({
    queryKey: [...KEY, "corrections"],
    queryFn: async () => (await api.get<Correction[]>("/work-plans/corrections")).data,
  });

/** Keputusan koreksi: respons server langsung menggantikan baris di daftar (tidak menunggu refetch,
 * yang bisa membawa data lama dan membuat klik pertama seolah tidak berefek), lalu daftar diperbarui ulang. */
export const useDecideCorrection = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, note, force }: { id: string; decision: CorrectionDecision; note?: string; force?: boolean }) =>
      (await api.post<Correction>(`/work-plans/corrections/${id}/decision`, { decision, note, force: force ?? false })).data,
    onSuccess: (updated) => {
      qc.setQueryData<Correction[]>([...KEY, "corrections"], (old) =>
        old?.map((c) => (c.correction_id === updated.correction_id ? updated : c)),
      );
      return qc.invalidateQueries({ queryKey: KEY });
    },
  });
};

export const CORRECTION_STATUS: Record<Correction["status"], string> = {
  REQUESTED: "Menunggu keputusan",
  REVISING: "Sedang direvisi ketua",
  IN_REVIEW: "Revisi menunggu pemeriksaan",
  ACCEPTED: "Diterima",
  REJECTED: "Ditolak",
};

/** Keputusan yang tersedia untuk PM menurut status koreksi. */
export function correctionActions(status: Correction["status"]): { decision: CorrectionDecision; label: string; needsNote: boolean }[] {
  if (status === "REQUESTED") {
    return [
      { decision: "APPROVE", label: "Setujui revisi", needsNote: false },
      { decision: "REJECT", label: "Tolak", needsNote: true },
    ];
  }
  if (status === "IN_REVIEW") {
    return [
      { decision: "ACCEPT", label: "Terima laporan", needsNote: false },
      { decision: "RETURN", label: "Kembalikan untuk revisi", needsNote: true },
    ];
  }
  return [];
}
