import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useKeysetList } from "@/hooks/useKeysetList";
import { api } from "@/lib/apiClient";
import { dateRangeError } from "@/lib/dateRange";
import type { components } from "@/lib/apiTypes";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { saveBlob } from "@/services/exportService";

export type Attendance = components["schemas"]["AttendanceResponse"];
export type AttendanceList = components["schemas"]["AttendanceListResponse"];
export const PAGE_SIZE = 50;

export interface AttendanceFilters {
  status: string;
  from: string;
  to: string;
  /** Cari nama/NIP (awalan). */
  q: string;
  /** mine = absensi pribadi, team = absensi anggota/umum, kosong = bawaan lama (tanpa pemisahan). */
  scope: "mine" | "team" | "";
}

/** GET /attendance — cakupan data ditentukan API (R-33); data lama tetap tampil saat berpindah halaman. */
export function useAttendance(f: AttendanceFilters) {
  const q = useDebouncedValue(f.q.trim(), 300);
  return useKeysetList<AttendanceList, AttendanceList>({
    key: ["attendance", "list"],
    url: "/attendance",
    enabled: !dateRangeError(f.from, f.to),
    params: {
      size: PAGE_SIZE,
      scope: f.scope || undefined,
      status: f.status || undefined,
      from: f.from || undefined,
      to: f.to || undefined,
      q: q || undefined,
    },
    // Ringkasan hari ini (today, laporan tertunda, dll.) diambil dari halaman pertama.
    merge: (pages) => ({ ...pages[0], items: pages.flatMap((p) => p.items) }),
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

/** GET /attendance/export — CSV absensi seluruh organisasi (izin export:attendance, Finance); berkas langsung terunduh. */
export async function exportAttendanceCsv(startDate: string, endDate: string): Promise<void> {
  const res = await api.get<Blob>("/attendance/export", {
    params: { start_date: startDate, end_date: endDate },
    responseType: "blob",
  });
  saveBlob(res.data, res.headers["content-disposition"] as string | undefined, `absensi-${startDate}_${endDate}.csv`);
}
