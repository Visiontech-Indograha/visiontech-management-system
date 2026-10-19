/**
 * web/src/services/workPlanV2Service.ts
 * Layanan komunikasi API untuk Work Plan V2 (Weekly, Daily, Item Multi-slot):
 * - Mengambil form options lengkap (divisi, tim, anggota, work types, completions, office sites, tools, armada)
 * - CRUD Weekly Plan
 * - CRUD Daily Plan
 * - CRUD Plan Item (Multi-slot)
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type {
  DailyPlanV2Value,
  PlanItemV2Value,
  WeeklyPlanV2Value,
  WeeklyCalendarMatrixValue,
  ProjectScheduleValue,
  BulkApproveDailyPlansValue,
} from "@/schemas/workPlanV2Schema";
export type {
  DailyPlanV2Value,
  PlanItemV2Value,
  WeeklyPlanV2Value,
  WeeklyCalendarMatrixValue,
  ProjectScheduleValue,
  BulkApproveDailyPlansValue,
};

export interface TeamMemberOption {
  employee_id: string;
  full_name: string;
  position: string;
}

export interface TeamOption {
  team_id: string;
  name: string;
  division_id: string;
  leader_employee_id: string;
  leader_name?: string;
  leader_position?: string;
  members: TeamMemberOption[];
}

export interface DivisionOption {
  division_id: string;
  name: string;
}

export interface WorkTypeOption {
  work_type_id: string;
  name: string;
  division_id: string;
  description?: string | null;
  image_requirements_count?: number;
}

export interface WorkCompletionOption {
  completion_id: string;
  client_name: string;
  project_title: string;
  order_number?: string | null;
  division_id?: string | null;
  order_status?: string;
}

export interface OfficeSiteOption {
  office_id: string;
  name: string;
  address?: string | null;
  latitude: number;
  longitude: number;
  radius_m?: number;
}

export interface ToolOption {
  tool_id: string;
  name: string;
  tool_code: string;
  division_id?: string | null;
  category?: string;
}

export interface VehicleOption {
  vehicle_id: string;
  name: string;
  number_plate: string;
  vehicle_type: string;
  division_id?: string | null;
}

export interface WorkPlanFormOptionsV2 {
  divisions: DivisionOption[];
  teams: TeamOption[];
  work_types: WorkTypeOption[];
  work_completions: WorkCompletionOption[];
  offices: OfficeSiteOption[];
  tools: ToolOption[];
  vehicles: VehicleOption[];
}

export interface WeeklyPlanDetailResponse extends WeeklyPlanV2Value {
  division_name?: string;
  team_name?: string;
  leader_name?: string;
  created_by_name?: string;
  approved_by_pm_name?: string;
  create_at?: string;
  update_at?: string;
}

export const planV2Keys = {
  options: ["work-plans-v2", "form-options"] as const,
  weeklyList: ["work-plans-v2", "weekly-list"] as const,
  weeklyDetail: (id: string) => ["work-plans-v2", "weekly-detail", id] as const,
  dailyList: (weeklyId: string) => ["work-plans-v2", "daily-list", weeklyId] as const,
  dailyDetail: (dailyId: string) => ["work-plans-v2", "daily-detail", dailyId] as const,
  itemList: (dailyId: string) => ["work-plans-v2", "item-list", dailyId] as const,
  matrix: (startDate: string, endDate: string, divisionId?: string, teamId?: string) =>
    ["work-plans-v2", "matrix", startDate, endDate, divisionId || "all", teamId || "all"] as const,
  projectSchedule: (completionId: string) =>
    ["work-plans-v2", "project-schedule", completionId] as const,
};

/** Ambil seluruh data dropdown master untuk form Rencana Kerja V2 */
export function useWorkPlanFormOptionsV2() {
  return useQuery({
    queryKey: planV2Keys.options,
    queryFn: async () => {
      const res = await api.get<WorkPlanFormOptionsV2>("/work-plans/form-options-v2");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Ambil rincian lengkap Weekly Plan V2 beserta hari dan slot tugas */
export function useWeeklyPlanV2Detail(id: string, enabled = true) {
  return useQuery({
    queryKey: planV2Keys.weeklyDetail(id),
    queryFn: async () => {
      const res = await api.get<WeeklyPlanDetailResponse>(`/work-plans/weekly/${id}`);
      return res.data;
    },
    enabled: Boolean(id) && enabled,
  });
}

/** Mutasi Buat Weekly Plan V2 (POST /work-plans/weekly) */
export function useCreateWeeklyPlanV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WeeklyPlanV2Value) => {
      const res = await api.post<WeeklyPlanDetailResponse>("/work-plans/weekly", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["work-plans"] });
      qc.invalidateQueries({ queryKey: planV2Keys.weeklyList });
    },
  });
}

/** Mutasi Ubah Weekly Plan V2 (PUT /work-plans/weekly/{id}) */
export function useUpdateWeeklyPlanV2(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<WeeklyPlanV2Value>) => {
      const res = await api.put<WeeklyPlanDetailResponse>(`/work-plans/weekly/${id}`, payload);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["work-plans"] });
      qc.invalidateQueries({ queryKey: planV2Keys.weeklyList });
      qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(id) });
      qc.setQueryData(planV2Keys.weeklyDetail(id), data);
    },
  });
}

/** Mutasi Hapus Weekly Plan V2 (DELETE /work-plans/weekly/{id}) */
export function useDeleteWeeklyPlanV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.delete(`/work-plans/weekly/${id}`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["work-plans"] });
      qc.invalidateQueries({ queryKey: planV2Keys.weeklyList });
    },
  });
}

// ── DAILY PLAN CRUD ─────────────────────────────────────────

/** Mutasi Tambah Hari Baru (POST /work-plans/daily) */
export function useCreateDailyPlanV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DailyPlanV2Value) => {
      const res = await api.post<DailyPlanV2Value>("/work-plans/daily", payload);
      return res.data;
    },
    onSuccess: (_, vars) => {
      if (vars.weekly_plan_id) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(vars.weekly_plan_id) });
        qc.invalidateQueries({ queryKey: ["plan-days", vars.weekly_plan_id] });
      }
    },
  });
}

/** Mutasi Ubah Hari Kerja (PUT /work-plans/daily/{id}) */
export function useUpdateDailyPlanV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<DailyPlanV2Value> }) => {
      const res = await api.put<DailyPlanV2Value>(`/work-plans/daily/${id}`, data);
      return res.data;
    },
    onSuccess: (updated) => {
      if (updated.weekly_plan_id) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(updated.weekly_plan_id) });
        qc.invalidateQueries({ queryKey: ["plan-days", updated.weekly_plan_id] });
      }
      if (updated.daily_plan_id) {
        qc.invalidateQueries({ queryKey: planV2Keys.dailyDetail(updated.daily_plan_id) });
      }
    },
  });
}

/** Mutasi Hapus Hari Kerja (DELETE /work-plans/daily/{id}) */
export function useDeleteDailyPlanV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, weeklyPlanId }: { id: string; weeklyPlanId?: string }) => {
      const res = await api.delete(`/work-plans/daily/${id}`);
      return { id, weeklyPlanId, ...res.data };
    },
    onSuccess: (data) => {
      if (data.weeklyPlanId) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(data.weeklyPlanId) });
        qc.invalidateQueries({ queryKey: ["plan-days", data.weeklyPlanId] });
      }
    },
  });
}

// ── PLAN ITEM CRUD ──────────────────────────────────────────

/** Mutasi Tambah Butir Tugas Baru (POST /work-plans/items) */
export function useCreatePlanItemV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PlanItemV2Value) => {
      const res = await api.post<PlanItemV2Value>("/work-plans/items", payload);
      return res.data;
    },
    onSuccess: (_, vars) => {
      if (vars.weekly_plan_id) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(vars.weekly_plan_id) });
        qc.invalidateQueries({ queryKey: ["plan-days", vars.weekly_plan_id] });
      }
      if (vars.daily_plan_id) {
        qc.invalidateQueries({ queryKey: ["daily-schedule-detail", vars.daily_plan_id] });
      }
    },
  });
}

/** Mutasi Ubah Butir Tugas (PUT /work-plans/items/{id}) */
export function useUpdatePlanItemV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<PlanItemV2Value> }) => {
      const res = await api.put<PlanItemV2Value>(`/work-plans/items/${id}`, data);
      return res.data;
    },
    onSuccess: (updated) => {
      if (updated.weekly_plan_id) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(updated.weekly_plan_id) });
        qc.invalidateQueries({ queryKey: ["plan-days", updated.weekly_plan_id] });
      }
      if (updated.daily_plan_id) {
        qc.invalidateQueries({ queryKey: ["daily-schedule-detail", updated.daily_plan_id] });
      }
    },
  });
}

/** Mutasi Hapus Butir Tugas (DELETE /work-plans/items/{id}) */
export function useDeletePlanItemV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, dailyPlanId, weeklyPlanId }: { id: string; dailyPlanId?: string; weeklyPlanId?: string }) => {
      const res = await api.delete(`/work-plans/items/${id}`);
      return { id, dailyPlanId, weeklyPlanId, ...res.data };
    },
    onSuccess: (data) => {
      if (data.weeklyPlanId) {
        qc.invalidateQueries({ queryKey: planV2Keys.weeklyDetail(data.weeklyPlanId) });
        qc.invalidateQueries({ queryKey: ["plan-days", data.weeklyPlanId] });
      }
      if (data.dailyPlanId) {
        qc.invalidateQueries({ queryKey: ["daily-schedule-detail", data.dailyPlanId] });
      }
    },
  });
}

// ── TASK CHAIN & WORK COMPLETION HOOKS ──────────────────────

/** Hook Query untuk status agregasi rantai tugas rollover (Task Chain) */
export function useTaskChainStatus(itemId: string | null) {
  return useQuery({
    queryKey: ["task-chain-status", itemId],
    queryFn: async () => {
      if (!itemId) return null;
      const res = await api.get(`/work-plans/items/${itemId}/chain-status`);
      return res.data;
    },
    enabled: Boolean(itemId),
  });
}

/** Hook Mutation untuk membuat Berita Acara Work Completion dari rantai tugas yang tuntas 100% */
export function useGenerateWorkCompletion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      payload,
    }: {
      itemId: string;
      payload?: { client_name?: string | null; project_title?: string | null };
    }) => {
      const res = await api.post(`/work-plans/items/${itemId}/generate-completion`, payload || {});
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["task-chain-status", vars.itemId] });
      qc.invalidateQueries({ queryKey: ["work-plans"] });
      qc.invalidateQueries({ queryKey: ["work-plans-v2"] });
      qc.invalidateQueries({ queryKey: ["daily-schedule-detail"] });
      qc.invalidateQueries({ queryKey: ["plan-days"] });
    },
  });
}

// ── DYNAMIC WEEKLY MATRIX & MULTI-WEEK PROJECT SCHEDULE HOOKS ──

/** Hook Query untuk kalender matriks mingguan dinamis (GET /work-plans/matrix) */
export function useWorkPlanMatrix({
  startDate,
  endDate,
  divisionId,
  teamId,
  enabled = true,
}: {
  startDate: string;
  endDate: string;
  divisionId?: string;
  teamId?: string;
  enabled?: boolean;
}) {
  return useQuery({
    queryKey: planV2Keys.matrix(startDate, endDate, divisionId, teamId),
    queryFn: async () => {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (divisionId) params.append("division_id", divisionId);
      if (teamId) params.append("team_id", teamId);
      const res = await api.get<WeeklyCalendarMatrixValue>(`/work-plans/matrix?${params.toString()}`);
      return res.data;
    },
    enabled: Boolean(startDate && endDate) && enabled,
  });
}

/** Hook Mutasi PM untuk Menyetujui Seluruh Hari Kerja dalam Rentang Tanggal (POST /work-plans/matrix/bulk-approve) */
export function useBulkApproveWeeklyMatrix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BulkApproveDailyPlansValue) => {
      const res = await api.post<{ success: boolean; approved_count: number; message: string }>(
        "/work-plans/matrix/bulk-approve",
        payload
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["work-plans-v2"] });
      qc.invalidateQueries({ queryKey: ["work-plans"] });
    },
  });
}

/** Hook Query untuk Linimasa & Akumulasi Proyek Multi-Minggu (GET /work-plans/project/{completionId}/schedule) */
export function useProjectSchedule(completionId?: string | null) {
  return useQuery({
    queryKey: planV2Keys.projectSchedule(completionId || ""),
    queryFn: async () => {
      if (!completionId) return null;
      const res = await api.get<ProjectScheduleValue>(`/work-plans/project/${completionId}/schedule`);
      return res.data;
    },
    enabled: Boolean(completionId),
  });
}


