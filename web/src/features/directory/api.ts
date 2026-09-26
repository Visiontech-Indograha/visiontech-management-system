import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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

/** Detail karyawan: baris dari daftar/cache bila ada, selain itu GET /employees/{id} (tautan langsung). */
export function useEmployee(id: string, fromList?: Employee) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["employee", id],
    queryFn: async () => {
      const cached = qc
        .getQueriesData<EmployeeList>({ queryKey: ["employees"] })
        .flatMap(([, data]) => data?.items ?? [])
        .find((e) => e.id === id);
      return cached ?? (await api.get<Employee>(`/employees/${id}`)).data;
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

/** HR memverifikasi/menolak berkas; hanya berkas terverifikasi yang berlaku (mis. SIM untuk pengemudi). */
export function useVerifyDocument(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ docId, ...body }: { docId: string; is_approved: boolean; review_note?: string | null }) =>
      (await api.post<EmployeeDocument>(`/employees/${employeeId}/documents/${docId}/verify`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-documents", employeeId] }),
  });
}

export const useUploadFile = () =>
  useMutation({
    mutationFn: async (form: FormData) => (await api.post<UploadedFile>("/files/upload", form)).data,
  });

/** HR menghapus karyawan yang sudah di-offboard (POST /employees/{id}/archive, V-29). */
export function useArchiveEmployee(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<{ id: string; message: string }>(`/employees/${id}/archive`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

/** HR memulihkan karyawan terhapus sebagai nonaktif (POST /employees/{id}/restore, V-29). */
export function useRestoreEmployee(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<{ id: string; message: string }>(`/employees/${id}/restore`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}
