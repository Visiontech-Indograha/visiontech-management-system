import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";
import { AbsenceResponse, LeaveCountResponse, LeaveRequestResponse } from "../../types/attendance";

export const useAttendanceHistory = () => {
  return useQuery({
    queryKey: ["attendance", "history"],
    queryFn: async () => {
      const { data } = await api.get<AbsenceResponse[]>("/api/v1/attendance/history");
      return data;
    },
  });
};

export const useLeaves = () => {
  return useQuery({
    queryKey: ["attendance", "leaves"],
    queryFn: async () => {
      const { data } = await api.get<LeaveRequestResponse[]>("/api/v1/attendance/leaves");
      return data;
    },
  });
};

export const useApproveLeave = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leaveId, status, notes }: { leaveId: string; status: string; notes?: string }) => {
      const { data } = await api.patch(`/api/v1/attendance/leaves/${leaveId}/approve`, {
        approval_status: status,
        notes: notes
      });
      return data;
    },
    onSuccess: () => {
      toast.success("Status cuti berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["attendance", "leaves"] });
      queryClient.invalidateQueries({ queryKey: ["attendance", "leave-balance"] });
    },
  });
};

export const useCancelLeave = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leaveId: string) => {
      await api.delete(`/api/v1/attendance/leaves/${leaveId}`);
    },
    onSuccess: () => {
      toast.success("Pengajuan cuti berhasil dibatalkan");
      queryClient.invalidateQueries({ queryKey: ["attendance", "leaves"] });
      queryClient.invalidateQueries({ queryKey: ["attendance", "leave-balance"] });
    },
  });
};

export const useLeaveBalance = (employeeId: string | undefined) => {
  return useQuery({
    queryKey: ["attendance", "leave-balance", employeeId],
    queryFn: async () => {
      const { data } = await api.get<LeaveCountResponse>(`/api/v1/attendance/leave-balance/${employeeId}`);
      return data;
    },
    enabled: !!employeeId,
  });
};

export interface AbsenceCorrection {
  status?: "PRESENT" | "LATE" | "ABSENT" | "LEAVE";
  check_out_time?: string;
}

export const useCorrectAbsence = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: AbsenceCorrection }) => {
      const res = await api.put<AbsenceResponse>(`/api/v1/attendance/history/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      toast.success("Absensi berhasil dikoreksi");
      queryClient.invalidateQueries({ queryKey: ["attendance", "history"] });
    },
  });
};

export const useDeleteAbsence = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/attendance/history/${id}`);
    },
    onSuccess: () => {
      toast.success("Absensi berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["attendance", "history"] });
    },
  });
};
