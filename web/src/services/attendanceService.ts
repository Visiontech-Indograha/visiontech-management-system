import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

export type Attendance = components["schemas"]["AttendanceResponse"];
export type AttendanceList = components["schemas"]["AttendanceListResponse"];
export const PAGE_SIZE = 50;

export interface AttendanceFilters {
  status: string;
  from: string;
  to: string;
  /** Cari nama/NIP (awalan). */
  q: string;
  page: number;
  /** mine = absensi pribadi, team = absensi anggota/umum, kosong = bawaan lama (tanpa pemisahan). */
  scope: "mine" | "team" | "";
}

/** GET /attendance — cakupan data ditentukan API (R-33); data lama tetap tampil saat berpindah halaman. */
export function useAttendance(f: AttendanceFilters) {
  const q = useDebouncedValue(f.q.trim(), 300);
  return useQuery({
    queryKey: ["attendance", { ...f, q }],
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
            ...(q ? { q } : {}),
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

export type ExplanationRequest = components["schemas"]["ExplanationRequest"];

/** POST /attendance/{id}/explain — karyawan memberi penjelasan atas absensi sendiri. */
export async function explainAttendance(id: string, body: ExplanationRequest): Promise<unknown> {
  return (await api.post(`/attendance/${id}/explain`, body)).data;
}

/** POST /attendance/{id}/review — peninjau menyetujui/menolak absensi. */
export async function reviewAttendance(id: string, body: components["schemas"]["ReviewRequest"]): Promise<unknown> {
  return (await api.post(`/attendance/${id}/review`, body)).data;
}

/** GET /attendance?employee_id= — absensi terbaru seorang karyawan (untuk kartu absen kantor). */
export async function listEmployeeAttendance(employeeId: string, size: number): Promise<AttendanceList> {
  return (await api.get<AttendanceList>("/attendance", { params: { employee_id: employeeId, size } })).data;
}

/** POST /attendance/check-in — absen masuk; waktu & jarak dihitung server (aturan inti #3). */
export async function checkIn(body: components["schemas"]["CheckInRequest"]): Promise<Attendance> {
  return (await api.post<Attendance>("/attendance/check-in", body)).data;
}

/** POST /attendance/check-out — absen pulang. */
export async function checkOut(body: components["schemas"]["CheckOutRequest"]): Promise<Attendance> {
  return (await api.post<Attendance>("/attendance/check-out", body)).data;
}

/** DELETE /attendance/{id} — SUPER_ADMIN menghapus permanen satu absensi. */
export async function deleteAttendance(id: string): Promise<unknown> {
  return (await api.delete(`/attendance/${id}`)).data;
}
