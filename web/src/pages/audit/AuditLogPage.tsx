import { useState } from "react";
import { AuditLogTemplate } from "@/components/templates/audit/AuditLogTemplate";
import { useAuditEvents } from "@/services/auditService";

/** Audit log perubahan data (GET /audit-events, izin view:audit). */
export function AuditLogPage() {
  const [entity, setEntity] = useState("");
  const [page, setPage] = useState(1);
  const logs = useAuditEvents(entity, page);
  const data = logs.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <AuditLogTemplate
      logs={logs}
      entity={entity}
      onEntityChange={(value) => {
        setEntity(value);
        setPage(1);
      }}
      page={page}
      lastPage={lastPage}
      onPageChange={setPage}
    />
  );
}
