import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";
import { WorkPlanResponse, ProgressReportResponse } from "../../types/fieldwork";

export interface WorkPlanListParams {
  q?: string;
  status_filter?: string;
  skip?: number;
  limit?: number;
}

export const useWorkPlans = (params: WorkPlanListParams = {}) => {
  return useQuery({
    queryKey: ["fieldwork", "work-plans", params],
    queryFn: async () => {
      const { data } = await api.get<WorkPlanResponse[]>("/api/v1/fieldwork/work-plans", { params });
      return data;
    },
    placeholderData: (prev) => prev,
  });
};

export const useWorkPlan = (id: string | undefined) => {
  return useQuery({
    queryKey: ["fieldwork", "work-plans", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<WorkPlanResponse>(`/api/v1/fieldwork/work-plans/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useProgressReports = () => {
  return useQuery({
    queryKey: ["fieldwork", "reports"],
    queryFn: async () => {
      const { data } = await api.get<ProgressReportResponse[]>("/api/v1/fieldwork/reports");
      return data;
    },
  });
};

export interface WorkPlanCreatePayload {
  title: string;
  description?: string;
  assignee_id?: string;
  planned_date?: string;
  status?: string;
  member_ids?: string[];
}

export type WorkPlanUpdatePayload = Partial<WorkPlanCreatePayload>;

export const useCreateWorkPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WorkPlanCreatePayload) => {
      const { data } = await api.post("/api/v1/fieldwork/work-plans", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Penugasan berhasil dibuat");
      queryClient.invalidateQueries({ queryKey: ["fieldwork", "work-plans"] });
    },
  });
};

export const useUpdateWorkPlan = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WorkPlanUpdatePayload) => {
      const { data } = await api.put(`/api/v1/fieldwork/work-plans/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Penugasan berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["fieldwork", "work-plans"] });
    },
  });
};

export const useDeleteWorkPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/fieldwork/work-plans/${id}`);
    },
    onSuccess: () => {
      toast.success("Penugasan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["fieldwork", "work-plans"] });
    },
  });
};

// ==================== Progress Report ====================

export const useProgressReport = (id: string | undefined) => {
  return useQuery({
    queryKey: ["fieldwork", "reports", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<ProgressReportResponse>(`/api/v1/fieldwork/reports/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useUpdateProgressReport = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { notes?: string; attachment_url?: string }) => {
      const { data } = await api.put(`/api/v1/fieldwork/reports/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Laporan berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["fieldwork", "reports"] });
    },
  });
};

export const useDeleteProgressReport = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/fieldwork/reports/${id}`);
    },
    onSuccess: () => {
      toast.success("Laporan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["fieldwork", "reports"] });
    },
  });
};
