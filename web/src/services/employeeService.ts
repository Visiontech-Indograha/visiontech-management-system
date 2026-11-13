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
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["employees"] }),
        qc.invalidateQueries({ queryKey: ["employee", employeeId] }),
        qc.invalidateQueries({ queryKey: ["employee-account", employeeId] }),
        qc.invalidateQueries({ queryKey: ["employee-account-sessions", employeeId] }),
      ]),
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

/** Peran lapangan akun (pilihan HR/SUPER_ADMIN). */
export type FieldRole = "EMPLOYEE" | "TEAM_LEADER";
export const FIELD_ROLE_LABEL: Record<FieldRole, string> = {
  EMPLOYEE: "Karyawan Lapangan",
  TEAM_LEADER: "Ketua tim",
};

/** Peran utama yang bisa ditetapkan dari kartu akun (Super Admin semua; HR hanya dua peran lapangan). */
export type PrimaryRole =
  | "OPERATIONAL_MANAGER" | "PROJECT_MANAGER" | "HSE" | "ADMIN_HR_GA" | "FINANCE" | "TEAM_LEADER" | "EMPLOYEE";
export const PRIMARY_ROLE_LABEL: Record<PrimaryRole, string> = {
  OPERATIONAL_MANAGER: "OM (Operational Manager)",
  PROJECT_MANAGER: "PM (Project Manager)",
  HSE: "HSE",
  ADMIN_HR_GA: "HR/GA",
  FINANCE: "Finance",
  TEAM_LEADER: "Ketua tim",
  EMPLOYEE: "Karyawan lapangan",
};

/** Buat akun / reset sandi / nonaktifkan / aktifkan / ubah peran lapangan. Sandi sementara hanya ada di respons. */
export function useAccountAction(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: AccountAction) => {
      const base = `/employees/${employeeId}/account`;
      switch (a.kind) {
        case "create":
          return (await api.post<AccountWithPassword>(base, { login: a.login, system_role: a.systemRole })).data;
        case "role":
          return (await api.post<Account>(`${base}/role`, { system_role: a.systemRole })).data;
        case "login":
          return (await api.post<Account>(`${base}/login`, { login: a.login })).data;
        case "revoke-session":
          return (await api.post<AccountSessionsRevoked>(`${base}/sessions/${a.sessionId}/revoke`)).data;
        case "revoke-all-sessions":
          return (await api.post<AccountSessionsRevoked>(`${base}/sessions/revoke-all`)).data;
        case "reset-device-slots":
          return (await api.post<AccountSessionsRevoked>(`${base}/device-slots/reset`)).data;
        case "unlock":
          return (await api.post<Account>(`${base}/unlock`)).data;
        case "reset":
          return (await api.post<AccountWithPassword>(`${base}/reset-password`)).data;
        case "deactivate":
        case "activate":
          return (await api.post<Account>(`${base}/${a.kind}`)).data;
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employee-account", employeeId] });
      qc.invalidateQueries({ queryKey: ["employee-account-sessions", employeeId] });
    },
  });
}

/** Aksi HR/admin atas akun karyawan; sandi sementara hanya ada di respons `create` & `reset`. */
export type AccountAction =
  | { kind: "create"; login: string; systemRole: FieldRole }
  | { kind: "role"; systemRole: PrimaryRole }
  | { kind: "login"; login: string }
  | { kind: "revoke-session"; sessionId: string }
  | { kind: "revoke-all-sessions" | "reset-device-slots" | "unlock" | "reset" | "deactivate" | "activate" };

export type AccountSession = S["AuthSessionResponseSchema"];
export type AccountSessionsRevoked = S["AccountSessionsRevoked"];

/** Batas perangkat aktif per akun di server (MAX_DEVICES di auth_service). */
export const DEVICE_SLOTS = 4;

/** Perangkat yang sedang masuk dengan akun karyawan (GET /employees/{id}/account/sessions, manage:users). */
export function useAccountSessions(employeeId: string, enabled = true) {
  return useQuery({
    queryKey: ["employee-account-sessions", employeeId],
    enabled,
    queryFn: async () => (await api.get<AccountSession[]>(`/employees/${employeeId}/account/sessions`)).data,
  });
}

/** Status wajah karyawan (GET /face/enrollments/{id}/status, manage:users). */
export function useEmployeeFaceStatus(employeeId: string) {
  return useQuery({
    queryKey: ["employee-face", employeeId],
    queryFn: async () => (await api.get<S["FaceStatus"]>(`/face/enrollments/${employeeId}/status`)).data,
  });
}

/** Atur ulang wajah karyawan agar bisa mendaftar ulang (DELETE /face/enrollments/{id}). */
export function useResetEmployeeFace(employeeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.delete<S["FaceResetResponse"]>(`/face/enrollments/${employeeId}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee-face", employeeId] }),
  });
}

/** Usulan nomor karyawan berikutnya (GET /employees/next-no); hanya saat formulir tambah dibuka. */
export function useNextEmployeeNo() {
  return useQuery({
    queryKey: ["employees", "next-no"],
    staleTime: 0,
    gcTime: 0,
    queryFn: async () => (await api.get<S["NextEmployeeNo"]>("/employees/next-no")).data.employee_no,
  });
}
