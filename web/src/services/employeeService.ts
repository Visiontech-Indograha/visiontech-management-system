import { useMemo } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/stores/sessionStore";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Employee = S["EmployeeOut"] & Partial<Pick<S["EmployeeDetail"], "addresses">>;
export type EmployeeDetail = S["EmployeeDetail"];
export type EmployeeList = S["EmployeeListResponse"];
export type EmployeeCreate = S["EmployeeCreate"];
export type EmployeeUpdate = S["EmployeeUpdate"];
export type Address = S["AddressOut"];
export type AddressIn = S["AddressIn"];
export type Division = S["DivisionOut"];
export type Office = S["OfficeResponse"];
export type JobPosition = S["JobPositionOut"];
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
  /** "" = semua yang belum diarsipkan; active | in_process | offboarded | archived. */
  status: string;
  page: number;
  division_id?: string;
  /** Ukuran halaman; pilihan tanpa pencarian memakai ukuran besar agar tidak ada karyawan yang terlewat. */
  size?: number;
}

export function useEmployees(f: EmployeeFilters) {
  return useQuery({
    queryKey: ["employees", f],
    queryFn: async () => {
      const params = {
        page: f.page,
        size: f.size ?? PAGE_SIZE,
        ...(f.status ? { status: f.status } : {}),
        ...(f.division_id ? { division_id: f.division_id } : {}),
        ...(f.q ? { q: f.q } : {}),
      };
      return (await api.get<EmployeeList>("/employees", { params })).data;
    },
    placeholderData: keepPreviousData,
  });
}

/** Detail karyawan + alamat (GET /employees/{id}); baris daftar dipakai sebagai tampilan awal. */
export function useEmployee(id: string, fromList?: Employee) {
  return useQuery({
    queryKey: ["employee", id],
    queryFn: async (): Promise<Employee> => (await api.get<EmployeeDetail>(`/employees/${id}`)).data,
    placeholderData: fromList,
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
    mutationFn: async (body: EmployeeUpdate) => (await api.put<EmployeeDetail>(`/employees/${id}`, body)).data,
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

/** HR/GA menonaktifkan dokumen (dicabut / tidak berlaku lagi). */
export function useDeactivateDocument(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (docId: string) =>
      (await api.post<EmployeeDocument>(`/employees/${employeeId}/documents/${docId}/deactivate`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-documents", employeeId] }),
  });
}

/** HR/GA menghapus dokumen yang salah unggah. */
export function useDeleteDocument(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (docId: string) => (await api.delete(`/employees/${employeeId}/documents/${docId}`)).data,
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

/** SUPER_ADMIN menghapus permanen karyawan yang sudah diarsipkan (DELETE /employees/{id}). */
export function useDeleteEmployee(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.delete<{ status: string }>(`/employees/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

/** SUPER_ADMIN menghapus permanen akun login karyawan (DELETE /employees/{id}/account). */
export function useDeleteAccount(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.delete<{ status: string }>(`/employees/${employeeId}/account`)).data,
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

/** Master V2 (Milestone 10): kantor, divisi, jabatan — pilihan form karyawan. */
export const useOffices = () =>
  useQuery({ queryKey: ["offices"], staleTime: 5 * 60_000, queryFn: async () => (await api.get<Office[]>("/offices")).data });

export const useDivisions = () =>
  useQuery({ queryKey: ["divisions"], staleTime: 5 * 60_000, queryFn: async () => (await api.get<Division[]>("/divisions")).data });

/** Hook untuk mendapatkan daftar divisi yang relevan dengan pengguna login (PM hanya melihat divisi yang dipimpinnya/dimilikinya). */
export function useUserDivisions(currentDivisionId?: string | null) {
  const query = useDivisions();
  const { me } = useSession();

  const userDivisions = useMemo(() => {
    const list = query.data ?? [];
    if (!query.data || me?.role !== "PROJECT_MANAGER") return list;
    return list.filter((u) => {
      const isPm = Boolean(me.employee_id && u.pm_id && String(u.pm_id).toLowerCase() === String(me.employee_id).toLowerCase());
      const isMyDiv = Boolean(me.division_id && String(u.id).toLowerCase() === String(me.division_id).toLowerCase());
      const isCurrent = Boolean(currentDivisionId && String(u.id).toLowerCase() === String(currentDivisionId).toLowerCase());
      return isPm || isMyDiv || isCurrent;
    });
  }, [query.data, me, currentDivisionId]);

  return {
    ...query,
    data: userDivisions,
    allDivisions: query.data ?? [],
  };
}

export const useJobPositions = () =>
  useQuery({
    queryKey: ["job-positions"],
    staleTime: 5 * 60_000,
    queryFn: async () => (await api.get<JobPosition[]>("/job-positions")).data,
  });

/** Alamat karyawan (HR): tambah / ubah / hapus. */
export function useAddressAction(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: { kind: "add"; body: AddressIn } | { kind: "update"; id: string; body: AddressIn } | { kind: "delete"; id: string }) => {
      const base = `/employees/${employeeId}/addresses`;
      if (a.kind === "add") return (await api.post<Address>(base, a.body)).data;
      if (a.kind === "update") return (await api.put<Address>(`${base}/${a.id}`, a.body)).data;
      return (await api.delete(`${base}/${a.id}`)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee", employeeId] }),
  });
}

/** HR: karyawan baru (POST /employees, manage:users) — M2-03. */
export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmployeeCreate) => (await api.post<EmployeeDetail>("/employees", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export type Account = S["AccountOut"];
export type AccountWithPassword = S["AccountWithPassword"];

/** M1-01 · akun login karyawan (GET /employees/{id}/account, manage:users). */
export const useAccount = (employeeId: string) =>
  useQuery({
    queryKey: ["employee-account", employeeId],
    queryFn: async () => (await api.get<Account>(`/employees/${employeeId}/account`)).data,
  });

/** Buat akun / reset password / nonaktifkan / aktifkan. Password sementara hanya ada di respons (sekali). */
export function useAccountAction(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: { kind: "create"; login: string } | { kind: "reset" | "deactivate" | "activate" }) => {
      const base = `/employees/${employeeId}/account`;
      if (a.kind === "create") return (await api.post<AccountWithPassword>(base, { login: a.login })).data;
      const path = a.kind === "reset" ? "reset-password" : a.kind;
      return (await api.post<Account | AccountWithPassword>(`${base}/${path}`)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-account", employeeId] }),
  });
}
