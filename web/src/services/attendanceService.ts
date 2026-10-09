import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Attendance = components["schemas"]["AttendanceResponse"];
export type AttendanceList = components["schemas"]["AttendanceListResponse"];
export const PAGE_SIZE = 50;

export interface AttendanceFilters {
  status: string;
  from: string;
  to: string;
  page: number;
  /** mine = absensi pribadi, team = absensi anggota/umum, kosong = bawaan lama (tanpa pemisahan). */
  scope: "mine" | "team" | "";
}

/** GET /attendance — cakupan data ditentukan API (R-33); data lama tetap tampil saat berpindah halaman. */
export function useAttendance(f: AttendanceFilters) {
  return useQuery({
    queryKey: ["attendance", f],
    queryFn: async () =>
      (
        await api.get<AttendanceList>("/attendance", {
          params: {
            page: f.page,
            size: PAGE_SIZE,
            ...(f.scope ? { scope: f.scope } : {}),
            ...(f.status ? { status: f.status } : {}),
            ...(f.from ? { from: f.from } : {}),
            ...(f.to ? { to: f.to } : {}),
          },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}

/** Mutasi absensi (tinjau/penjelasan) yang menyegarkan daftar & rekap absensi setelah berhasil. */
export function useAttendanceAction<V>(fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["attendance"] });
      await qc.invalidateQueries({ queryKey: ["attendance-recap"] });
    },
  });
}
