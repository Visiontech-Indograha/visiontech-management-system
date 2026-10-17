import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface ClearanceItem {
  id: string;
  offboarding_id: string;
  category: "TOOL" | "VEHICLE" | "DOCUMENTS" | "FINANCE" | "OTHER";
  item_name: string;
  is_cleared: boolean;
  cleared_by?: string;
  cleared_at?: string;
  notes?: string;
}

export interface Offboarding {
  id: string;
  employee_id: string;
  employee_name?: string;
  resignation_date: string;
  last_working_date: string;
  reason?: string;
  status: "INITIATED" | "IN_CLEARANCE" | "APPROVED" | "REJECTED";
  created_at?: string;
  clearance_items?: ClearanceItem[];
}

export interface OffboardingCreate {
  employee_id: string;
  resignation_date: string;
  last_working_date: string;
  reason?: string;
}

const KEY = ["offboardings"] as const;

export const useOffboardings = () =>
  useQuery({
    queryKey: KEY,
    queryFn: async () => (await api.get<Offboarding[]>("/offboarding")).data,
  });

export function useCreateOffboarding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: OffboardingCreate) => (await api.post<Offboarding>("/offboarding", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useVerifyClearanceItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, isCleared, notes }: { itemId: string; isCleared: boolean; notes?: string }) => {
      await api.post(`/offboarding/clearance/${itemId}/verify`, { is_cleared: isCleared, notes });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useApproveOffboarding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, approved, notes }: { id: string; approved: boolean; notes?: string }) => {
      await api.post(`/offboarding/${id}/decision`, { approved, notes });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
