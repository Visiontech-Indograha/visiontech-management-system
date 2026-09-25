import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type Employee = S["EmployeeResponse"];
export type EmployeeList = S["EmployeeListResponse"];
export type EmployeeUpdate = S["EmployeeUpdate"];
export type EmployeeDocument = S["EmployeeDocumentResponse"];
export type EmployeeDocumentCreate = S["EmployeeDocumentCreate"];
type DocumentList = S["DocumentListResponse"];

/** POST /files/upload belum punya skema respons di OpenAPI; bentuknya dari api/app/api/files.py. */
interface UploadedFile {
  file_id: string;
  message: string;
}

export const PAGE_SIZE = 25;

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
        size: PAGE_SIZE,
        ...(is_active !== undefined ? { is_active } : {}),
        ...(f.q ? { q: f.q } : {}),
      };
      return (await api.get<EmployeeList>("/employees", { params })).data;
    },
    placeholderData: keepPreviousData,
  });
}

/**
 * API tidak punya GET /employees/{id}. Detail memakai baris yang dibawa dari daftar
 * (state navigasi) atau yang masih tersimpan di cache daftar; tanpa itu → minta buka dari Direktori.
 */
export function useEmployee(id: string, fromList?: Employee) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["employee", id],
    queryFn: () => {
      const cached = qc
        .getQueriesData<EmployeeList>({ queryKey: ["employees"] })
        .flatMap(([, data]) => data?.items ?? [])
        .find((e) => e.id === id);
      if (cached) return cached;
      throw new ApiError("NOT_FOUND", "Buka data karyawan dari Direktori.", 404);
    },
    initialData: fromList,
    staleTime: Infinity,
    retry: false,
  });
}

export function useEmployeeDocuments(employeeId: string, enabled = true) {
  return useQuery({
    queryKey: ["employee-documents", employeeId],
    enabled,
    queryFn: async () => (await api.get<DocumentList>(`/employees/${employeeId}/documents`)).data,
  });
}

export function useUpdateEmployee(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmployeeUpdate) => (await api.put<Employee>(`/employees/${id}`, body)).data,
    onSuccess: async (employee) => {
      qc.setQueryData(["employee", id], employee);
      await qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}

export function useCreateDocument(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmployeeDocumentCreate) =>
      (await api.post<EmployeeDocument>(`/employees/${employeeId}/documents`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-documents", employeeId] }),
  });
}

export const useUploadFile = () =>
  useMutation({
    mutationFn: async (form: FormData) => (await api.post<UploadedFile>("/files/upload", form)).data,
  });
