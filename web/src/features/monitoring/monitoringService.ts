import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type TimelineGroup = components["schemas"]["TimelineGroup"];
export type AttendanceRecap = components["schemas"]["AttendanceRecap"];

export const useTimeline = (f: { from: string; to: string }) =>
  useQuery({
    queryKey: ["timeline", f],
    queryFn: async () =>
      (await api.get<TimelineGroup[]>("/timeline", { params: { ...(f.from ? { from: f.from } : {}), ...(f.to ? { to: f.to } : {}) } })).data,
  });

export const useAttendanceRecap = (month: string) =>
  useQuery({
    queryKey: ["attendance-recap", month],
    queryFn: async () => (await api.get<AttendanceRecap>("/recaps/attendance", { params: month ? { month } : {} })).data,
  });
