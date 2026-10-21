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

export interface WorkCompletionBom {
  bom_id: string;
  completion_id: string;
  work_plan_item_id?: string | null;
  material_code?: string | null;
  material_name: string;
  estimated_qty: number;
  actual_qty: number;
  unit: string;
  category?: string | null;
  notes?: string | null;
  sort_order: number;
  create_at?: string;
  update_at?: string;
}

export interface WorkCompletionDetail extends WorkCompletionOrder {
  completed_target_unit: number;
  start_work_date?: string | null;
  end_work_date?: string | null;
  obstacles?: string | null;
  summary_notes?: string | null;
  leader_signer_id?: string | null;
  leader_signed_at?: string | null;
  pm_signer_id?: string | null;
  pm_signer_name?: string | null;
  pm_signed_at?: string | null;
  signature_hash?: string | null;
  bom_items?: WorkCompletionBom[];
}

export interface CreateWorkCompletionBomIn {
  work_plan_item_id?: string | null;
  material_code?: string | null;
  material_name: string;
  estimated_qty: number;
  actual_qty?: number;
  unit?: string;
  category?: string | null;
  notes?: string | null;
  sort_order?: number;
}

export interface UpdateWorkCompletionBomIn {
  estimated_qty?: number;
  actual_qty?: number;
  unit?: string;
  category?: string | null;
  notes?: string | null;
  sort_order?: number;
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
      const res = await api.get<WorkCompletionDetail>(`/work-completions/${id}`);
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

export function useWorkCompletionBom(completionId: string) {
  return useQuery({
    queryKey: ["work-completion-bom", completionId],
    queryFn: async () => {
      const res = await api.get<WorkCompletionBom[]>(`/work-completions/${completionId}/bom`);
      return res.data;
    },
    enabled: !!completionId,
  });
}

export function useCreateWorkCompletionBom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      completionId,
      payload,
    }: {
      completionId: string;
      payload: CreateWorkCompletionBomIn;
    }) => {
      const res = await api.post<WorkCompletionBom>(
        `/work-completions/${completionId}/bom`,
        payload
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-completion-bom", vars.completionId] });
      qc.invalidateQueries({ queryKey: completionKey(vars.completionId) });
    },
  });
}

export function useUpdateWorkCompletionBom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      bomId: string;
      completionId: string;
      payload: UpdateWorkCompletionBomIn;
    }) => {
      const res = await api.put<WorkCompletionBom>(
        `/work-completions/bom/${vars.bomId}`,
        vars.payload
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-completion-bom", vars.completionId] });
      qc.invalidateQueries({ queryKey: completionKey(vars.completionId) });
    },
  });
}

export function useDeleteWorkCompletionBom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      bomId: string;
      completionId: string;
    }) => {
      await api.delete(`/work-completions/bom/${vars.bomId}`);
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-completion-bom", vars.completionId] });
      qc.invalidateQueries({ queryKey: completionKey(vars.completionId) });
    },
  });
}

export function useSyncBomFromWorkTypes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      completionId,
      overwrite_existing = false,
    }: {
      completionId: string;
      overwrite_existing?: boolean;
    }) => {
      const res = await api.post<{ synced_count: number; message: string }>(
        `/work-completions/${completionId}/sync-bom`,
        { overwrite_existing }
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-completion-bom", vars.completionId] });
      qc.invalidateQueries({ queryKey: completionKey(vars.completionId) });
    },
  });
}
