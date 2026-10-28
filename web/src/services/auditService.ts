import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type AuditEventList = components["schemas"]["AuditEventListResponse"];

/** GET /audit-events — 25 per halaman, opsional disaring per entitas, kata kunci (awalan aksi/tabel/pelaku), dan rentang tanggal; data lama tetap tampil saat berpindah halaman. */
export interface AuditFilters {
  entity: string;
  page: number;
  q?: string;
  dateFrom?: string;
  dateTo?: string;
}

export function useAuditEvents({ entity, page, q, dateFrom, dateTo }: AuditFilters) {
  return useQuery({
    queryKey: ["audit-events", entity, page, q ?? "", dateFrom ?? "", dateTo ?? ""],
    queryFn: async () =>
      (
        await api.get<AuditEventList>("/audit-events", {
          params: {
            page,
            size: 25,
            ...(entity ? { entity_type: entity } : {}),
            ...(q ? { q } : {}),
            ...(dateFrom ? { date_from: dateFrom } : {}),
            ...(dateTo ? { date_to: dateTo } : {}),
          },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}
