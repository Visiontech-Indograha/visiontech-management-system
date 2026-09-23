import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api";
import { CompanyExperience, CompanyExperienceCreate, CategoryCE } from "../../types/portofolio";

export function useCompanyExperiences() {
  return useQuery({
    queryKey: ["company_experiences"],
    queryFn: async () => {
      const res = await api.get<CompanyExperience[]>("/api/v1/portofolio/");
      return res.data;
    },
  });
}

export function useCreateCompanyExperience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CompanyExperienceCreate) => {
      const res = await api.post<CompanyExperience>("/api/v1/portofolio/", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company_experiences"] });
    },
  });
}

export function useUpdateCompanyExperience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<CompanyExperienceCreate> }) => {
      const res = await api.put<CompanyExperience>(`/api/v1/portofolio/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company_experiences"] });
    },
  });
}

export function useDeleteCompanyExperience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/portofolio/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company_experiences"] });
    },
  });
}

export function useCategoryCE() {
  return useQuery({
    queryKey: ['category_ce'],
    queryFn: async () => {
      const res = await api.get<CategoryCE[]>('/api/v1/portofolio/categories/all');
      return res.data;
    },
  });
}
