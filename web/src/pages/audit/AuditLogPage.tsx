import { AuditLogTemplate } from "@/components/templates/audit/AuditLogTemplate";
import { useListControls } from "@/hooks/useListControls";
import { AUDIT_ENTITIES } from "@/lib/auditLabels";
import { useAuditEvents } from "@/services/auditService";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Audit log perubahan data (GET /audit-events, izin view:audit); cari, entitas, dan rentang tanggal tersinkron ke URL. */
export function AuditLogPage() {
  const controls = useListControls({ size: 25, prefix: "aud_" });
  const entity = controls.filter("entity", Object.keys(AUDIT_ENTITIES));
  const from = controls.filter("from");
  const to = controls.filter("to");
  const dateFrom = DATE.test(from) ? from : "";
  const dateTo = DATE.test(to) ? to : "";
  const logs = useAuditEvents({ entity, page: controls.page, q: controls.search, dateFrom, dateTo });
  const data = logs.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <AuditLogTemplate
      logs={logs}
      controls={controls}
      entity={entity}
      dateFrom={dateFrom}
      dateTo={dateTo}
      invalidRange={Boolean(dateFrom && dateTo && dateFrom > dateTo)}
      lastPage={lastPage}
    />
  );
}
