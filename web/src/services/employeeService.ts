import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Employee = S["EmployeeResponse"];
export type EmployeeList = S["EmployeeListResponse"];
export type EmployeeUpdate = S["EmployeeUpdate"];
export type EmployeeDocument = S["EmployeeDocumentResponse"];
export type EmployeeDocumentCreate = S["EmployeeDocumentCreate"];
export type EmergencyContact = S["EmergencyContactResponse"];
export type EmergencyContactCreate = S["EmergencyContactCreate"];
export type EmergencyContactUpdate = S["EmergencyContactUpdate"];
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

export type Assignment = S["EmployeeAssignmentResponse"];
export type Unit = S["UnitOut"];

/** Unit organisasi (GET /units) — pilihan unit mutasi/promosi & nama unit karyawan. */
export const useUnits = () =>
  useQuery({ queryKey: ["units"], staleTime: 5 * 60_000, queryFn: async () => (await api.get<Unit[]>("/units")).data });

/** Riwayat jabatan/penempatan, terbaru dulu (GET /employees/{id}/assignments). */
export const useAssignments = (employeeId: string) =>
  useQuery({
    queryKey: ["employee-assignments", employeeId],
    queryFn: async () => (await api.get<Assignment[]>(`/employees/${employeeId}/assignments`)).data,
  });

/** HR: mutasi/promosi (POST /employees/{id}/assignments, domain.js PROMOTE). */
export function usePromoteEmployee(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: S["EmployeeAssignmentCreate"]) =>
      (await api.post<Assignment>(`/employees/${employeeId}/assignments`, body)).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["employee", employeeId] });
      await qc.invalidateQueries({ queryKey: ["employee-assignments", employeeId] });
      await qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}

/** HR: karyawan baru (POST /employees, manage:users) — M2-03. */
export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: S["EmployeeCreate"]) => (await api.post<Employee>("/employees", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employees"] }),
  });
}

/** HR: akhiri masa kerja (POST /employees/{id}/offboard, domain.js OFFBOARD) — M2-02. Akses login ikut dicabut. */
export function useOffboardEmployee(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) => (await api.post(`/employees/${employeeId}/offboard`, { reason })).data,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["employee", employeeId] });
      await qc.invalidateQueries({ queryKey: ["employees"] });
    },
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

/** Kontak darurat karyawan (GET /employees/{id}/emergency-contacts). */
export function useEmergencyContacts(employeeId: string) {
  return useQuery({
    queryKey: ["employee-emergency-contacts", employeeId],
    queryFn: async () =>
      (await api.get<EmergencyContact[]>(`/employees/${employeeId}/emergency-contacts`)).data,
  });
}

/** Tambah kontak darurat (POST /employees/{id}/emergency-contacts). */
export function useCreateEmergencyContact(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmergencyContactCreate) =>
      (await api.post<EmergencyContact>(`/employees/${employeeId}/emergency-contacts`, body)).data,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["employee-emergency-contacts", employeeId] }),
  });
}

/** Ubah kontak darurat (PUT /employees/{id}/emergency-contacts/{contactId}). */
export function useUpdateEmergencyContact(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ contactId, ...body }: { contactId: string } & EmergencyContactUpdate) =>
      (await api.put<EmergencyContact>(`/employees/${employeeId}/emergency-contacts/${contactId}`, body)).data,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["employee-emergency-contacts", employeeId] }),
  });
}

/** Hapus kontak darurat (DELETE /employees/{id}/emergency-contacts/{contactId}). */
export function useDeleteEmergencyContact(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (contactId: string) =>
      (await api.delete<{ message: string }>(`/employees/${employeeId}/emergency-contacts/${contactId}`)).data,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["employee-emergency-contacts", employeeId] }),
  });
}

