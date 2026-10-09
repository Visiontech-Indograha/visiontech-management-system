import { useState } from "react";
import { ListPagination } from "@/components/organisms/ListPagination";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useAuditEvents } from "@/services/auditService";
import { AuditEntityFilter } from "@/components/organisms/audit/AuditEntityFilter";
import { AuditLogTable } from "@/components/organisms/audit/AuditLogTable";

/** Audit log perubahan data (GET /audit-events, izin view:audit). */
export function AuditLogPage() {
  const [entity, setEntity] = useState("");
  const [page, setPage] = useState(1);
  const logs = useAuditEvents(entity, page);
  const data = logs.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <PageTemplate title="Audit log">
      <AuditEntityFilter
        entity={entity}
        onEntityChange={(value) => {
          setEntity(value);
          setPage(1);
        }}
      />
      <AuditLogTable logs={logs} />
      {data && data.total > data.size && (
        <ListPagination total={data.total} noun="catatan" page={page} shownPage={data.page} lastPage={lastPage} onPageChange={setPage} />
      )}
    </PageTemplate>
  );
}
