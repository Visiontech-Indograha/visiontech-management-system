import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

/** Ringkasan Beranda (R-12) dari endpoint yang sudah ada. */
export type AttendanceList = components["schemas"]["AttendanceListResponse"];
export type ExpiringList = components["schemas"]["ExpiringDocumentList"];

/** Jumlah absensi berstatus NEEDS_REVIEW (izin review:attendance). */
export function useAttendanceToReview(enabled: boolean) {
  return useQuery({
    queryKey: ["attendance", { status: "NEEDS_REVIEW", home: true }],
    enabled,
    queryFn: async () => (await api.get<AttendanceList>("/attendance", { params: { status: "NEEDS_REVIEW", page: 1, size: 1 } })).data.total,
  });
}
/** Dokumen karyawan kedaluwarsa atau berakhir ≤ 30 hari (GET /documents/expiring, izin manage:employee_documents). */
export function useExpiringDocuments(enabled: boolean) {
  return useQuery({
    queryKey: ["documents", "expiring"],
    enabled,
    queryFn: async () =>
      (await api.get<ExpiringList>("/documents/expiring")).data.items,
  });
}


export type HomeSummary = components["schemas"]["HomeSummary"];
/** Ringkasan antrean per peran (GET /home/summary); disegarkan tiap 60 dtk dan saat jendela aktif kembali. */
export function useHomeSummary(enabled = true) {
  return useQuery({
    queryKey: ["home", "summary"],
    enabled,
    refetchInterval: 60_000,
    queryFn: async () => (await api.get<HomeSummary>("/home/summary")).data,
  });
}
