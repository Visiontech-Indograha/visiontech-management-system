import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type AuditEventList = components["schemas"]["AuditEventListResponse"];

/** GET /audit-events — 25 per halaman, opsional disaring per entitas; data lama tetap tampil saat berpindah halaman. */
export function useAuditEvents(entity: string, page: number) {
  return useQuery({
    queryKey: ["audit-events", entity, page],
    queryFn: async () =>
      (
        await api.get<AuditEventList>("/audit-events", {
          params: { page, size: 25, ...(entity ? { entity_type: entity } : {}) },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}
