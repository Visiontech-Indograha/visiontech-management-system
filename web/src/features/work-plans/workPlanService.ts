import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type WorkPlan = S["WorkPlanResponse"];
export type WorkPlanCreate = S["WorkPlanCreate"];
export type WorkPlanUpdate = S["WorkPlanUpdate"];
export type DayPlanRequest = S["DayPlanRequest"];
export type TeamRequest = S["TeamRequest"];
type Employee = S["EmployeeResponse"];
type EmployeeList = S["EmployeeListResponse"];
type Site = S["SiteResponse"];
type Asset = S["AssetListItem"];
export type AssignmentOptions = S["PlanAssignmentOptions"];

/** Transisi SK yang memakai TransitionRequest {row_version, reason}. */
export type Transition =
  | "publish"
  | "accept"
  | "appeal"
  | "revise"
  | "start"
  | "cancel"
  | "archive"
  | "restore"
  | "approve-completion"
  | "return-completion";

export const planKey = (id: string) => ["work-plan", id] as const;

export function useWorkPlans(f: { status: string; archived: boolean }) {
  return useQuery({
    queryKey: ["work-plans", f],
    queryFn: async () =>
      (
        await api.get<WorkPlan[]>("/work-plans", {
          params: { archived: f.archived, ...(f.status ? { status_filter: f.status } : {}) },
        })
      ).data,
  });
}

export const useWorkPlan = (id: string) =>
  useQuery({ queryKey: planKey(id), queryFn: async () => (await api.get<WorkPlan>(`/work-plans/${id}`)).data });

/** Karyawan aktif untuk pilihan PM/ketua/anggota (GET /employees, maks. 100 per halaman). */
export const useActiveEmployees = () =>
  useQuery({
    queryKey: ["employees", "active-options"],
    queryFn: async () =>
      (await api.get<EmployeeList>("/employees", { params: { is_active: true, size: 100 } })).data.items,
    staleTime: 5 * 60 * 1000,
  });

export const useSiteOptions = () =>
  useQuery({ queryKey: ["sites"], queryFn: async () => (await api.get<Site[]>("/sites")).data });

export const useAssignmentOptions = (periodStart: string, periodEnd: string) =>
  useQuery({
    queryKey: ["plan-assignment-options", periodStart, periodEnd],
    queryFn: async () =>
      (
        await api.get<AssignmentOptions>("/work-plans/assignment-options", {
          params: { period_start: periodStart, period_end: periodEnd },
        })
      ).data,
    enabled: Boolean(periodStart && periodEnd && periodEnd >= periodStart),
  });

export const useAvailableVehicles = () =>
  useQuery({
    queryKey: ["assets", "available-vehicles"],
    queryFn: async () => (await api.get<Asset[]>("/assets")).data,
    select: (assets) => assets.filter((asset) => asset.kind === "VEHICLE" && asset.status === "AVAILABLE" && !asset.allocation_id),
  });

/** Peta id → nama karyawan untuk menampilkan PM/ketua. */
export function employeeName(list: Employee[] | undefined, id: string | null | undefined): string {
  if (!id) return "-";
  return list?.find((e) => e.id === id)?.full_name ?? "Karyawan lain";
}

function useSetPlan() {
  const qc = useQueryClient();
  return async (plan: WorkPlan) => {
    qc.setQueryData(planKey(plan.id), plan);
    await qc.invalidateQueries({ queryKey: ["work-plans"] });
    // Terbit/terima menandatangani dokumen di server; muat ulang daftar dokumennya.
    await qc.invalidateQueries({ queryKey: ["plan-documents", plan.id] });
    // Laporan akhir, tim, aset, isi SK, dan usulan ikut berubah saat transisi (mis. penutupan disetujui).
    await qc.invalidateQueries({ queryKey: planKey(plan.id) });
    await qc.invalidateQueries({ queryKey: planDetailKey(plan.id) });
    await qc.invalidateQueries({ queryKey: ["plan-changes", plan.id] });
  };
}

export function useCreatePlan() {
  const setPlan = useSetPlan();
  return useMutation({
    mutationFn: async (body: WorkPlanCreate) => (await api.post<WorkPlan>("/work-plans", body)).data,
    onSuccess: setPlan,
  });
}

export function useCreatePlanWithTeam() {
  const setPlan = useSetPlan();
  return useMutation({
    mutationFn: async ({
      plan: body,
      leader_employee_id,
      member_employee_ids,
      vehicle_id,
      driver_employee_id,
    }: {
      plan: WorkPlanCreate;
      leader_employee_id: string;
      member_employee_ids: string[];
      vehicle_id?: string;
      driver_employee_id?: string;
    }) => {
      const plan = (await api.post<WorkPlan>("/work-plans", body)).data;
      const team = (
        await api.put<S["TeamResponse"]>(`/work-plans/${plan.id}/members`, {
          leader_employee_id,
          member_employee_ids,
          row_version: plan.row_version,
        })
      ).data;
      if (vehicle_id) {
        await api.post(`/assets/${vehicle_id}/reserve`, {
          work_plan_id: plan.id,
          driver_employee_id,
        });
      }
      return { ...plan, leader_employee_id: team.leader_employee_id, row_version: team.row_version };
    },
    onSuccess: setPlan,
  });
}

export function useUpdatePlan(id: string) {
  const setPlan = useSetPlan();
  return useMutation({
    mutationFn: async (body: WorkPlanUpdate) => (await api.patch<WorkPlan>(`/work-plans/${id}`, body)).data,
    onSuccess: setPlan,
  });
}

export function useTransition(id: string) {
  const setPlan = useSetPlan();
  return useMutation({
    mutationFn: async ({ action, row_version, reason = "" }: { action: Transition; row_version: number; reason?: string }) =>
      (await api.post<WorkPlan>(`/work-plans/${id}/${action}`, { row_version, reason })).data,
    onSuccess: setPlan,
  });
}

/** Tambah hari (POST /days) lalu isi judul + tugasnya (PUT /days/{day}/plan). */
export function useAddDay(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ work_date, title, tasks }: { work_date: string; title: string; tasks: string[] }) => {
      const day = (await api.post<S["PlanDayResponse"]>(`/work-plans/${id}/days`, { work_date, title })).data;
      const body: DayPlanRequest = { title, tasks: tasks.map((t) => ({ title: t })) };
      await api.put(`/work-plans/${id}/days/${day.id}/plan`, body);
      return day;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: planKey(id) });
      await qc.invalidateQueries({ queryKey: ["plan-days", id] });
    },
  });
}

export function useSetTeam(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TeamRequest) => (await api.put<S["TeamResponse"]>(`/work-plans/${id}/members`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: planKey(id) }),
  });
}

// ── Alur SK v2 (keputusan pemilik 2026-10-03, flowchart SK2) ─────────────────────────────────
export type PlanFormOptions = S["PlanFormOptions"];
export type PlanDraftRequest = S["PlanDraftRequest"];
export type PlanDetail = S["PlanDetailOut"];
export type FormPerson = S["FormPerson"];
export type FormAsset = S["FormAsset"];

export const planDetailKey = (id: string) => ["work-plan-detail", id] as const;

/** Pilihan form Buat/Ubah SK: kategori, lokasi, ketua, anggota, alat, kendaraan (sudah disaring server). */
export const usePlanFormOptions = (planId?: string) =>
  useQuery({
    queryKey: ["plan-form-options", planId ?? "new"],
    queryFn: async () =>
      (await api.get<PlanFormOptions>("/work-plans/form-options", { params: planId ? { plan_id: planId } : {} })).data,
  });

/** Calon driver (dari ketua + anggota terpilih) yang ber-SIM sesuai tipe kendaraan dan tidak terikat SK lain. */
export const useDriverOptions = (q: { vehicleId: string; periodEnd: string; candidates: string[]; planId?: string }) =>
  useQuery({
    queryKey: ["plan-driver-options", q],
    queryFn: async () =>
      (
        await api.get<string[]>("/work-plans/driver-options", {
          params: {
            vehicle_id: q.vehicleId,
            period_end: q.periodEnd,
            candidate_ids: q.candidates,
            ...(q.planId ? { plan_id: q.planId } : {}),
          },
          paramsSerializer: { indexes: null },
        })
      ).data,
    enabled: Boolean(q.vehicleId && q.periodEnd && q.candidates.length),
  });

export const usePlanDetail = (id: string, enabled = true) =>
  useQuery({
    queryKey: planDetailKey(id),
    queryFn: async () => (await api.get<PlanDetail>(`/work-plans/${id}/detail`)).data,
    enabled: Boolean(id) && enabled,
  });

/** Simpan SK lengkap dalam satu transaksi: buat (POST /full) atau ubah draf (PUT /{id}/full). */
export function useSavePlanDraft(planId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlanDraftRequest) =>
      planId
        ? (await api.put<PlanDetail>(`/work-plans/${planId}/full`, body)).data
        : (await api.post<PlanDetail>("/work-plans/full", body)).data,
    onSuccess: async (detail) => {
      const id = String(detail.plan.id);
      qc.setQueryData(planDetailKey(id), detail);
      await qc.invalidateQueries({ queryKey: planKey(id) });
      await qc.invalidateQueries({ queryKey: ["work-plans"] });
      await qc.invalidateQueries({ queryKey: ["plan-form-options"] });
      await qc.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}

/** Riwayat revisi rencana kerja (GET /work-plans/{id}/revisions). */
export type PlanRevision = S["PlanRevisionOut"];
export const revisionsKey = (planId: string) => ["plan-revisions", planId] as const;
export const usePlanRevisions = (planId: string) =>
  useQuery({
    queryKey: revisionsKey(planId),
    queryFn: async () => (await api.get<PlanRevision[]>(`/work-plans/${planId}/revisions`)).data,
  });

/** PM merevisi rencana kerja kapan saja (POST /work-plans/{id}/revisions); `change_id` = permintaan ketua yang selesai. */
export function useRevisePlan(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlanDraftRequest & { reason: string; change_id?: string | null }) =>
      (await api.post<PlanDetail>(`/work-plans/${planId}/revisions`, body)).data,
    onSuccess: async (detail) => {
      qc.setQueryData(planDetailKey(planId), detail);
      await qc.invalidateQueries({ queryKey: planKey(planId) });
      await qc.invalidateQueries({ queryKey: ["work-plans"] });
      await qc.invalidateQueries({ queryKey: ["plan-changes", planId] });
      await qc.invalidateQueries({ queryKey: ["plan-documents", planId] });
      await qc.invalidateQueries({ queryKey: ["plan-days", planId] });
      await qc.invalidateQueries({ queryKey: revisionsKey(planId) });
    },
  });
}

/** PM menerima adendum ketua dengan mengubah isi SK yang sedang berjalan (PUT /amendments/{changeId}). */
export function useApplyAmendment(planId: string, changeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlanDraftRequest) =>
      (await api.put<PlanDetail>(`/work-plans/${planId}/amendments/${changeId}`, body)).data,
    onSuccess: async (detail) => {
      qc.setQueryData(planDetailKey(planId), detail);
      await qc.invalidateQueries({ queryKey: planKey(planId) });
      await qc.invalidateQueries({ queryKey: ["plan-changes", planId] });
      await qc.invalidateQueries({ queryKey: ["plan-documents", planId] });
      await qc.invalidateQueries({ queryKey: ["plan-days", planId] });
    },
  });
}

/** HTML A4 (pratinjau draf atau dokumen terbit beserta TTD) untuk ditampilkan di iframe. */
export const useHtmlDocument = (path: string | null) =>
  useQuery({
    queryKey: ["html-document", path],
    queryFn: async () => (await api.get<string>(path ?? "", { responseType: "text" })).data,
    enabled: Boolean(path),
    staleTime: 0,
  });
