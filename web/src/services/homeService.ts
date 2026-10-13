import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

/** Ringkasan Beranda (R-12) dari endpoint yang sudah ada. */
export type AttendanceList = components["schemas"]["AttendanceListResponse"];
export type ExpiringList = components["schemas"]["ExpiringDocumentList"];
export type PendingList = components["schemas"]["PendingDocumentList"];

/** Jumlah absensi berstatus NEEDS_REVIEW (izin review:attendance). */
export function useAttendanceToReview(enabled: boolean) {
  return useQuery({
    queryKey: ["attendance", { status: "NEEDS_REVIEW", home: true }],
    enabled,
    queryFn: async () => (await api.get<AttendanceList>("/attendance", { params: { status: "NEEDS_REVIEW", page: 1, size: 1 } })).data.total,
  });
}
/** M2: dokumen pribadi kedaluwarsa atau berakhir ≤ 30 hari (GET /documents/expiring, izin verify:documents). */
export function useExpiringDocuments(enabled: boolean) {
  return useQuery({
    queryKey: ["documents", "expiring"],
    enabled,
    queryFn: async () =>
      (await api.get<ExpiringList>("/documents/expiring")).data.items.filter((d) => d.urgency !== "AMAN"),
  });
}

/** P2-5: antrean verifikasi HR — dokumen pribadi berstatus PENDING (GET /documents/pending). */
export function usePendingDocuments(enabled: boolean) {
  return useQuery({
    queryKey: ["documents", "pending"],
    enabled,
    queryFn: async () => (await api.get<PendingList>("/documents/pending")).data.items,
  });
}
