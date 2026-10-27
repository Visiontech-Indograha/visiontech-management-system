import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export type ProjectStatus = "DRAFT" | "ONGOING" | "COMPLETED" | "CANCELLED";

export interface Project {
  project_id: string;
  client_id: string;
  client_name: string;
  office_id: string;
  office_name: string;
  division_id: string;
  division_name: string;
  pm_id: string;
  pm_name: string;
  spk_number: string;
  project_title: string;
  total_target_qty: number;
  unit_measure: string;
  start_date: string;
  end_date: string;
  status: ProjectStatus;
  daily_plan_count: number;
  order_count: number;
}

export interface ProjectFilter {
  division_id?: string;
  client_id?: string;
  status?: string;
  q?: string;
}

export interface ProjectInput {
  client_id: string;
  office_id: string;
  division_id: string;
  pm_id?: string | null;
  spk_number: string;
  project_title: string;
  total_target_qty: number;
  unit_measure: string;
  start_date: string;
  end_date: string;
  status?: ProjectStatus;
}

const KEY = ["projects"] as const;

export const useProjects = (filter?: ProjectFilter) =>
  useQuery({
    queryKey: [...KEY, filter],
    queryFn: async () =>
      (
        await api.get<Project[]>("/projects", {
          params: {
            ...(filter?.division_id ? { division_id: filter.division_id } : {}),
            ...(filter?.client_id ? { client_id: filter.client_id } : {}),
            ...(filter?.status ? { status: filter.status } : {}),
            ...(filter?.q ? { q: filter.q } : {}),
          },
        })
      ).data,
  });

export function useSaveProject(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProjectInput) =>
      id
        ? (await api.put<Project>(`/projects/${id}`, body)).data
        : (await api.post<Project>("/projects", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
