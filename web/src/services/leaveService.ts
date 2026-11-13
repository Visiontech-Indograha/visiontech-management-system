import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { idempotencyHeaders } from "@/lib/idempotency";
import { getPaged, type Paged } from "@/lib/paged";

export interface LeaveRequest {
  leave_id: string;
  employee_id: string;
  employee_name: string;
  employee_no?: string;
  employee_photo_file_id?: string | null;
  division_name?: string;
  leave_type: "ANNUAL" | "SICK" | "MATERNITY" | "UNPAID" | "OTHER";
  start_date: string;
  end_date: string;
  total_days: number;
  reason: string;
  status: "PENDING" | "APPROVED_BY_PM" | "APPROVED_BY_HR" | "APPROVED_BY_FINANCE" | "REJECTED" | "CANCELLED";
  attachment_path?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  rejection_note?: string | null;
  review_note?: string | null;
  cancel_note?: string | null;
  conflicts?: LeaveConflict[];
  create_at: string;
}

/** Jadwal tim (APPROVED/ONGOING) yang bertabrakan dengan hari cuti karyawan. */
export interface LeaveConflict {
  plan_id: string;
  work_date: string;
  team_name: string;
  status: string;
}

export interface LeaveBalance {
  balance_id: string;
  employee_id: string;
  employee_name: string;
  period_year: number;
  total_quota: number;
  used_quota: number;
  remaining_quota: number;
}

export interface LeaveCreateInput {
  employee_id?: string;
  leave_type: "ANNUAL" | "SICK" | "MATERNITY" | "UNPAID" | "OTHER";
  start_date: string;
  end_date: string;
  reason: string;
  attachment_file_id?: string;
}

export interface LeaveReviewInput {
  decision: "APPROVED" | "REJECTED";
  note?: string;
  acknowledge_conflicts?: boolean;
}

export interface LeaveListParams {
  employee_id?: string;
  status?: string;
  year?: number;
  leave_type?: string;
  q?: string;
  page?: number;
  size?: number;
}

export async function listLeaves(params: LeaveListParams = {}): Promise<Paged<LeaveRequest>> {
  return getPaged<LeaveRequest>("/leaves", { ...params });
}

export async function getLeave(leaveId: string): Promise<LeaveRequest> {
  return (await api.get<LeaveRequest>(`/leaves/${leaveId}`)).data;
}

export async function applyLeave(
  { idempotencyKey, ...body }: LeaveCreateInput & { idempotencyKey?: string },
): Promise<LeaveRequest> {
  return (await api.post<LeaveRequest>("/leaves", body, { headers: idempotencyHeaders(idempotencyKey) })).data;
}

export async function reviewLeave(leaveId: string, body: LeaveReviewInput): Promise<LeaveRequest> {
  return (await api.post<LeaveRequest>(`/leaves/${leaveId}/review`, body)).data;
}

export async function cancelLeave(leaveId: string, reason?: string): Promise<LeaveRequest> {
  return (await api.post<LeaveRequest>(`/leaves/${leaveId}/cancel`, reason ? { reason } : {})).data;
}

export async function getLeaveBalance(employeeId: string, year = new Date().getFullYear()): Promise<LeaveBalance> {
  return (await api.get<LeaveBalance>(`/leaves/balances/${employeeId}`, { params: { year } })).data;
}

export const useLeaves = (params?: LeaveListParams, opts?: { enabled?: boolean }) =>
  useQuery({
    queryKey: ["leaves", params],
    queryFn: () => listLeaves(params),
    placeholderData: (prev) => prev,
    enabled: opts?.enabled ?? true,
  });

export const useLeaveBalance = (employeeId: string, year = new Date().getFullYear()) =>
  useQuery({
    queryKey: ["leave-balance", employeeId, year],
    queryFn: () => getLeaveBalance(employeeId, year),
    enabled: Boolean(employeeId),
  });

export function useLeaveMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: applyLeave,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["leaves"] });
      await qc.invalidateQueries({ queryKey: ["leave-balance"] });
    },
  });
}

export function useReviewLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leaveId, body }: { leaveId: string; body: LeaveReviewInput }) =>
      reviewLeave(leaveId, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["leaves"] });
      await qc.invalidateQueries({ queryKey: ["leave-balance"] });
    },
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leaveId, reason }: { leaveId: string; reason?: string }) => cancelLeave(leaveId, reason),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["leaves"] });
      await qc.invalidateQueries({ queryKey: ["leave-balance"] });
    },
  });
}

/** Label jenis cuti/izin untuk tampilan. */
export const LEAVE_TYPE_LABEL: Record<string, string> = {
  ANNUAL: "Cuti Tahunan",
  SICK: "Izin Sakit",
  MATERNITY: "Cuti Melahirkan",
  UNPAID: "Cuti di Luar Tanggungan",
  OTHER: "Izin Khusus",
};
