import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface WorkCompletionOrder {
  completion_id: string;
  division_id?: string | null;
  division_name?: string | null;
  pm_id?: string | null;
  pm_name?: string | null;
  client_name: string;
  project_title: string;
  order_number?: string | null;
  total_target_unit: number;
  completed_unit?: number;
  unit_measure: string;
  order_status: "PENDING_CLIENT" | "ONGOING" | "URGENT" | "COMPLETED" | "CANCELLED";
  priority_level: "NORMAL" | "HIGH" | "URGENT";
  site_address?: string | null;
  site_lat?: number | null;
  site_lng?: number | null;
  create_at?: string;
}

export type WorkCompletion = WorkCompletionOrder;
export type WorkCompletionListResponse = WorkCompletionOrder[];

export interface WorkCompletionCreate {
  client_name: string;
  project_title: string;
  total_target_unit: number;
  unit_measure?: string;
  division_id?: string | null;
  pm_id?: string | null;
  order_number?: string | null;
  priority_level?: string;
  site_address?: string | null;
  site_lat?: number | null;
  site_lng?: number | null;
}

export const completionKey = (id: string) => ["work-completion", id] as const;

export function useWorkCompletions(filters?: {
  client_name?: string;
  order_status?: string;
  division_id?: string;
}) {
  return useQuery({
    queryKey: ["work-completions", filters],
    queryFn: async () => {
      const res = await api.get<WorkCompletionOrder[]>("/work-completions", {
        params: filters,
      });
      return res.data;
    },
  });
}

export function useWorkCompletion(id: string) {
  return useQuery({
    queryKey: completionKey(id),
    queryFn: async () => {
      const res = await api.get<WorkCompletionOrder>(`/work-completions/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateWorkCompletion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WorkCompletionCreate) => {
      const res = await api.post<WorkCompletionOrder>("/work-completions", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["work-completions"] });
    },
  });
}

export function useUpdateWorkCompletionStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await api.patch<WorkCompletionOrder>(`/work-completions/${id}/status`, { status });
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-completions"] });
      qc.invalidateQueries({ queryKey: completionKey(vars.id) });
    },
  });
}
