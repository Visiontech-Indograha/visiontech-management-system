import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type AttendanceRecap = components["schemas"]["AttendanceRecap"];
export type OvertimeRecapRow = components["schemas"]["OvertimeRecapRow"];

/** GET /recaps/overtime — rekap lembur per karyawan per bulan (bulan kosong = semua). */
export const useOvertimeRecap = (month: string) =>
  useQuery({
    queryKey: ["overtime-recap", month],
    queryFn: async () => (await api.get<OvertimeRecapRow[]>("/recaps/overtime", { params: month ? { month } : {} })).data,
  });

export const useAttendanceRecap = (month: string) =>
  useQuery({
    queryKey: ["attendance-recap", month],
    queryFn: async () => (await api.get<AttendanceRecap>("/recaps/attendance", { params: month ? { month } : {} })).data,
  });
