import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";

export type HESLaggingType =
  | "P3K_CASE"
  | "NEAR_MISS"
  | "RECORDABLE_CASE"
  | "ENVIRONMENTAL_INCIDENT"
  | "FIRE_EXPLOSION"
  | "PROPERTY_DAMAGE";

export type HESLeadingType =
  | "MEETING"
  | "INSPECTION_AUDIT"
  | "FIT_FOR_DUTY"
  | "HES_CAMPAIGN"
  | "EMPLOYEE_ORIENTATION"
  | "REPORTING";

export interface HESLaggingItem {
  indicator_type: HESLaggingType;
  month: number;
  count: number;
}

export interface HESLeadingItem {
  activity_type: HESLeadingType;
  month: number;
  actual: number;
  target: number;
}

export interface HESPlan {
  id: string;
  year: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  lagging_indicators: (HESLaggingItem & { id: string; hes_plan_id: string })[];
  leading_indicators: (HESLeadingItem & { id: string; hes_plan_id: string })[];
}

export const useHesPlans = () => {
  return useQuery({
    queryKey: ["hes", "plans"],
    queryFn: async () => {
      const { data } = await api.get<HESPlan[]>("/api/v1/hes/plans");
      return data;
    },
  });
};

export const useHesPlanByYear = (year: number) => {
  return useQuery({
    queryKey: ["hes", "plans", "by-year", year],
    queryFn: async () => {
      const { data } = await api.get<HESPlan>(`/api/v1/hes/plans/by-year/${year}`, {
        suppressErrorToast: true,
      });
      return data;
    },
    retry: false,
  });
};

export const useCreateHesPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { year: number; notes?: string }) => {
      const { data } = await api.post<HESPlan>("/api/v1/hes/plans", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("HES Plan berhasil dibuat");
      queryClient.invalidateQueries({ queryKey: ["hes", "plans"] });
    },
  });
};

export const useDeleteHesPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/hes/plans/${id}`);
    },
    onSuccess: () => {
      toast.success("HES Plan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["hes", "plans"] });
    },
  });
};

export const useUpsertHesIndicators = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      planId,
      lagging,
      leading,
    }: {
      planId: string;
      lagging: HESLaggingItem[];
      leading: HESLeadingItem[];
    }) => {
      const { data } = await api.put<HESPlan>(`/api/v1/hes/plans/${planId}/indicators`, { lagging, leading });
      return data;
    },
    onSuccess: () => {
      toast.success("Indikator HES berhasil disimpan");
      queryClient.invalidateQueries({ queryKey: ["hes", "plans"] });
    },
  });
};
