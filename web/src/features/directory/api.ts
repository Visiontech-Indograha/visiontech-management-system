import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type Employee = S["EmployeeOut"];
export interface EmployeeDocument {
  id: string;
  employee_id: string;
  doc_type: string;
  number_masked: string;
  expiry_date: string | null;
  status: string;
  lifecycle: string;
  file_id: string;
  uploaded_by: string;
  verified_by: string | null;
  verified_at: string | null;
  review_note: string | null;
  created_at: string;
}
type EmployeePage = S["Page_EmployeeOut_"];

export interface EmployeeFilters {
  q?: string;
  status: string;
  page: number;
}

export function useEmployees(f: EmployeeFilters) {
  return useQuery({
    queryKey: ["employees", f],
    queryFn: async () => {
      const is_active = f.status === "active" ? true : f.status === "inactive" ? false : undefined;
      const params = {
        page: f.page,
        size: 25,
        ...(is_active !== undefined ? { is_active } : {}),
        ...(f.q ? { q: f.q } : {}),
      };
      return (await api.get<EmployeePage>("/employees", { params })).data;
    },
    placeholderData: keepPreviousData,
  });
}

export const useEmployee = (id: string) =>
  useQuery({ queryKey: ["employee", id], queryFn: async () => (await api.get<Employee>(`/employees/${id}`)).data });

export function useEmployeeDocuments(id: string, enabled = true) {
  return useQuery({
    queryKey: ["employee-documents", id],
    enabled,
    queryFn: async () => (await api.get<{ items: EmployeeDocument[]; total: number }>(`/employees/${id}/documents`)).data,
  });
}

function useInvalidating<V, D>(fn: (v: V) => Promise<D>, keys: string[][]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => Promise.all(keys.map((queryKey) => qc.invalidateQueries({ queryKey }))),
  });
}

const DOC_KEYS = [["employee-documents"], ["employee"], ["employees"], ["me-docs"]];

export const useUpdateProfile = (id: string) =>
  useInvalidating(
    async (body: Record<string, unknown>) => (await api.patch<Employee>(`/employees/${id}/profile`, body)).data,
    [["employee"], ["employees"]],
  );

export const useCreateDocument = (userId: string) =>
  useInvalidating(
    async (body: { doc_type: string; number: string; expiry_date?: string | null; file_id: string }) =>
      (await api.post<EmployeeDocument>(`/employees/${userId}/documents`, body)).data,
    DOC_KEYS,
  );

export const useUploadFile = () => {
  return useMutation({
    mutationFn: async (form: FormData) => (await api.post<{ id: string; url: string; mime_type: string }>("/files/upload", form)).data,
  });
};
