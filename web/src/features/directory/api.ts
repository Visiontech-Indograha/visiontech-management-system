import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type Employee = S["EmployeeOut"];
export type EmployeeDocument = S["EmployeeDocumentOut"];
export type DocumentType = S["DocumentTypeOut"];
export type Incomplete = S["IncompleteOut"];
export type Completeness = S["CompletenessOut"];
type EmployeePage = S["Page_EmployeeOut_"];

export interface EmployeeFilters {
  q?: string;
  role?: string;
  employment_type?: string;
  status: string;
  page: number;
}

export function useEmployees(f: EmployeeFilters) {
  return useQuery({
    queryKey: ["employees", f],
    queryFn: async () => {
      const params = {
        page: f.page,
        page_size: 25,
        status: f.status,
        ...(f.q ? { q: f.q } : {}),
        ...(f.role ? { role: f.role } : {}),
        ...(f.employment_type ? { employment_type: f.employment_type } : {}),
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
    queryFn: async () => (await api.get<EmployeeDocument[]>(`/employees/${id}/documents`)).data,
  });
}

function useInvalidating<V, D>(fn: (v: V) => Promise<D>, keys: string[][]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => Promise.all(keys.map((queryKey) => qc.invalidateQueries({ queryKey }))),
  });
}

const DOC_KEYS = [["employee-documents"], ["employee"], ["employees"], ["incomplete"], ["me-docs"]];

export const useUpdateProfile = (id: string) =>
  useInvalidating(
    async (body: Record<string, unknown>) => (await api.patch<Employee>(`/employees/${id}/profile`, body)).data,
    [["employee"], ["employees"]],
  );

export const useCreateDocument = (userId: string) =>
  useInvalidating(
    async (form: FormData) => (await api.post<EmployeeDocument>(`/employees/${userId}/documents`, form)).data,
    DOC_KEYS,
  );

export const useUpdateDocument = (userId: string) =>
  useInvalidating(
    async ({ id, form }: { id: string; form: FormData }) =>
      (await api.patch<EmployeeDocument>(`/employees/${userId}/documents/${id}`, form)).data,
    DOC_KEYS,
  );

export const useDeleteDocument = (userId: string) =>
  useInvalidating(async (id: string) => api.delete(`/employees/${userId}/documents/${id}`), DOC_KEYS);

export function useDocumentTypes(enabled = true) {
  return useQuery({
    queryKey: ["document-types"],
    enabled,
    queryFn: async () => (await api.get<DocumentType[]>("/document-types")).data,
  });
}

export const useIncomplete = () =>
  useQuery({ queryKey: ["incomplete"], queryFn: async () => (await api.get<Incomplete[]>("/documents/incomplete")).data });

export function useMyCompleteness(userId: string | undefined) {
  return useQuery({
    queryKey: ["me-docs", userId],
    enabled: !!userId,
    queryFn: async () => (await api.get<Completeness>(`/employees/${userId}/documents/completeness`)).data,
  });
}

export const useSaveType = () =>
  useInvalidating(
    async ({ id, body }: { id?: string; body: Record<string, unknown> }) =>
      id ? (await api.patch<DocumentType>(`/document-types/${id}`, body)).data : (await api.post<DocumentType>("/document-types", body)).data,
    [["document-types"], ["incomplete"], ["employees"]],
  );

export const useDeleteType = () =>
  useInvalidating(async (id: string) => api.delete(`/document-types/${id}`), [["document-types"], ["incomplete"], ["employees"]]);
