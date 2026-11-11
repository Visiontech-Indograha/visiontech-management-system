import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { saveBlob } from "./exportService";

export type WorkOrderStatus =
  | "WAITING_SURVEY"
  | "SURVEY_IN_PROGRESS"
  | "SURVEY_SUBMITTED"
  | "READY_TO_EXECUTE"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "BAST_SIGNED"
  | "CANCELLED";

export interface WorkOrderItem {
  item_id: string;
  work_order_id: string;
  survey_point_id?: string | null;
  work_type_id: string;
  work_type_name?: string | null;
  title: string;
  location_detail?: string | null;
  target_qty: number;
  completed_qty: number;
  photo_slots_snapshot: Array<Record<string, unknown>>;
  status: "PENDING" | "IN_PROGRESS" | "DONE";
  created_at: string;
}

export interface WorkOrderBom {
  bom_id: string;
  work_order_id: string;
  work_order_item_id?: string | null;
  item_name: string;
  unit: string;
  estimated_qty: number;
  actual_qty: number;
}

export interface SurveyPoint {
  point_id: string;
  work_order_id: string;
  survey_id?: string | null;
  point_name: string;
  location_detail?: string | null;
  site_lat?: number | null;
  site_lng?: number | null;
  recommended_work_type_id?: string | null;
  recommended_work_type_name?: string | null;
  recommended_bom: Array<Record<string, unknown>>;
  remarks?: string | null;
  photos: Array<Record<string, unknown>>;
  status: string;
}

export interface WorkOrder {
  work_order_id: string;
  wo_number: string;
  client_id: string;
  client_name?: string | null;
  client_site_id?: string | null;
  site_name?: string | null;
  site_address?: string | null;
  site_lat?: number | null;
  site_lng?: number | null;
  division_id: string;
  division_name?: string | null;
  pm_id: string;
  pm_name?: string | null;
  lead_team_id?: string | null;
  team_name?: string | null;
  title: string;
  initial_complaint?: string | null;
  status: WorkOrderStatus;
  survey_assigned_at?: string | null;
  survey_submitted_at?: string | null;
  survey_approved_at?: string | null;
  bast_signed_at?: string | null;
  bast_signer_name?: string | null;
  total_items: number;
  completed_items: number;
  created_at: string;
}

export interface WorkOrderDetail extends WorkOrder {
  survey_points: SurveyPoint[];
  items: WorkOrderItem[];
  bom: WorkOrderBom[];
}

export interface WorkOrderCreateInput {
  client_id: string;
  client_site_id?: string | null;
  division_id: string;
  pm_id: string;
  title: string;
  initial_complaint?: string | null;
  lead_team_id?: string | null;
}

export interface AssignSurveyInput {
  lead_team_id: string;
  survey_date: string;
  notes?: string | null;
}

export interface SignBastInput {
  signer_name: string;
  signature_data_uri?: string | null;
  notes?: string | null;
}

const KEY = ["work_orders"] as const;

export function useWorkOrders(params?: {
  division_id?: string;
  status?: string;
  client_id?: string;
  q?: string;
}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<WorkOrder[]>("/work-orders", { params });
      return res.data;
    },
  });
}

export function useWorkOrderDetail(workOrderId?: string) {
  return useQuery({
    queryKey: [...KEY, "detail", workOrderId],
    queryFn: async () => {
      if (!workOrderId) return null;
      const res = await api.get<WorkOrderDetail>(`/work-orders/${workOrderId}`);
      return res.data;
    },
    enabled: Boolean(workOrderId),
  });
}

export function useCreateWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WorkOrderCreateInput) => {
      const res = await api.post<WorkOrderDetail>("/work-orders", payload);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useAssignSurvey(workOrderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssignSurveyInput) => {
      const res = await api.post<WorkOrderDetail>(`/work-orders/${workOrderId}/assign-survey`, payload);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useApplySurvey(workOrderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<WorkOrderDetail>(`/work-orders/${workOrderId}/apply-survey`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useSignBast(workOrderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SignBastInput) => {
      const res = await api.post<WorkOrderDetail>(`/work-orders/${workOrderId}/sign-bast`, payload);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export async function downloadWorkOrderExport(
  workOrderId: string,
  template: string,
  fallbackName = "dokumen.bin",
): Promise<void> {
  const res = await api.get<Blob>(`/work-orders/${workOrderId}/export/${template}`, {
    responseType: "blob",
  });
  saveBlob(res.data, res.headers["content-disposition"] as string | undefined, fallbackName);
}
