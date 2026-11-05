import { useKeysetList } from "@/hooks/useKeysetList";
import type { components } from "@/lib/apiTypes";

export type AuditEventList = components["schemas"]["AuditEventListResponse"];

/** GET /audit-events — keyset 25 per muatan, opsional disaring per entitas, kata kunci (awalan aksi/tabel/pelaku), dan rentang tanggal. Tanpa total. */
export interface AuditFilters {
  entity: string;
  q?: string;
  dateFrom?: string;
  dateTo?: string;
}

export const AUDIT_SIZE = 25;

export function useAuditEvents({ entity, q, dateFrom, dateTo }: AuditFilters) {
  return useKeysetList<AuditEventList, AuditEventList>({
    key: ["audit-events"],
    url: "/audit-events",
    params: {
      size: AUDIT_SIZE,
      entity_type: entity || undefined,
      q: q || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    },
    merge: (pages) => ({ ...pages[0], items: pages.flatMap((p) => p.items) }),
  });
}
