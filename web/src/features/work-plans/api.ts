import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type WorkPlan = S["WorkPlanResponse"];
export type WorkPlanCreate = S["WorkPlanCreate"];
export type WorkPlanUpdate = S["WorkPlanUpdate"];
export type DayPlanRequest = S["DayPlanRequest"];
export type TeamRequest = S["TeamRequest"];
type Employee = S["EmployeeResponse"];
type EmployeeList = S["EmployeeListResponse"];
type Site = S["SiteResponse"];

/** Transisi SK yang memakai TransitionRequest {row_version, reason}. */
export type Transition = "publish" | "accept" | "appeal" | "revise" | "start" | "cancel" | "archive" | "restore";

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
  };
}

export function useCreatePlan() {
  const setPlan = useSetPlan();
  return useMutation({
    mutationFn: async (body: WorkPlanCreate) => (await api.post<WorkPlan>("/work-plans", body)).data,
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
    onSuccess: () => qc.invalidateQueries({ queryKey: planKey(id) }),
  });
}

export function useSetTeam(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TeamRequest) => (await api.put<S["TeamResponse"]>(`/work-plans/${id}/members`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: planKey(id) }),
  });
}
