import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type AttendanceItem = S["AttendanceListItem"];
export type AttendanceRow = S["AttendanceOut"];
export type Policy = S["PolicyOut"];

export interface AttendanceFilters {
  from?: string;
  to?: string;
  role?: string;
  flagged?: string; // "true" | "false" | ""
  page: number;
}

const clean = (o: Record<string, unknown>) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v != null));

export function useAttendanceList(f: AttendanceFilters) {
  return useQuery({
    queryKey: ["attendance", f],
    queryFn: async () =>
      (await api.get<S["Page_AttendanceListItem_"]>("/attendance", { params: clean({ ...f, page_size: 25 }) })).data,
    placeholderData: keepPreviousData,
  });
}

export const usePolicy = () =>
  useQuery({ queryKey: ["attendance-policy"], queryFn: async () => (await api.get<Policy>("/attendance/policy")).data });

export const useMyAttendance = () =>
  useQuery({ queryKey: ["attendance-me"], queryFn: async () => (await api.get<AttendanceRow[]>("/attendance/me")).data });

/** Selfie butuh token: ambil sebagai blob lalu tampilkan lewat object URL. */
export function useSelfie(attendanceId: string | null) {
  return useQuery({
    queryKey: ["attendance-selfie", attendanceId],
    enabled: !!attendanceId,
    staleTime: Infinity,
    queryFn: async () => {
      const r = await api.get<Blob>(`/attendance/${attendanceId}/selfie`, { responseType: "blob" });
      return URL.createObjectURL(r.data);
    },
  });
}

export function useCorrection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await api.post<AttendanceRow>("/attendance/corrections", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["attendance"] }),
  });
}

/** Unduh ekspor (butuh header Authorization, jadi tidak bisa memakai tautan biasa). */
export async function downloadExport(params: { from: string; to: string; format: "xlsx" | "csv"; role?: string }) {
  const r = await api.get<Blob>("/attendance/export", { params: clean(params), responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `absensi_${params.from}_${params.to}.${params.format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const FLAG_LABEL: Record<string, string> = {
  MOCK_APP_INSTALLED: "Aplikasi lokasi palsu terpasang",
  DEVELOPER_MODE: "Mode pengembang aktif",
  ROOTED: "Perangkat di-root",
  CLIENT_TIME_SKEW: "Jam perangkat berbeda dari server",
  DEVICE_CHANGED: "Perangkat berbeda dari absen sebelumnya",
  WEB_SOURCE: "Absen melalui web",
};
