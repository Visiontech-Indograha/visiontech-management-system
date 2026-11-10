import { AuditLogTemplate } from "@/components/templates/audit/AuditLogTemplate";
import { useListControls } from "@/hooks/useListControls";
import { AUDIT_FILTER_ENTITIES } from "@/lib/auditLabels";
import { resolveAuditSearch } from "@/lib/auditChanges";
import { useAuditEvents } from "@/services/auditService";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Audit log perubahan data (GET /audit-events keyset, izin view:audit); cari, entitas, dan rentang tanggal tersinkron ke URL. */
export function AuditLogPage() {
  const controls = useListControls({ size: 25, prefix: "aud_" });
  const entity = controls.filter("entity", Object.keys(AUDIT_FILTER_ENTITIES));
  const from = controls.filter("from");
  const to = controls.filter("to");
  const dateFrom = DATE.test(from) ? from : "";
  const dateTo = DATE.test(to) ? to : "";
  const { query, more } = useAuditEvents({ entity, q: resolveAuditSearch(controls.search), dateFrom, dateTo });

  return (
    <AuditLogTemplate
      logs={query}
      more={more}
      controls={controls}
      entity={entity}
      dateFrom={dateFrom}
      dateTo={dateTo}
      invalidRange={Boolean(dateFrom && dateTo && dateFrom > dateTo)}
    />
  );
}
