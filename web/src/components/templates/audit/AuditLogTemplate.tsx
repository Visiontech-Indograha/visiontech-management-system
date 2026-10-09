import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { AuditEntityFilter } from "@/components/organisms/audit/AuditEntityFilter";
import { AuditLogTable } from "@/components/organisms/audit/AuditLogTable";
import type { AuditEventList } from "@/services/auditService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka audit log: saringan entitas, tabel catatan, halaman. */
export function AuditLogTemplate({ logs, entity, onEntityChange, page, lastPage, onPageChange }: {
  logs: UseQueryResult<AuditEventList>;
  entity: string;
  onEntityChange: (entity: string) => void;
  page: number;
  lastPage: number;
  onPageChange: (page: number) => void;
}) {
  const data = logs.data;
  return (
    <PageTemplate title="Audit log">
      <AuditEntityFilter entity={entity} onEntityChange={onEntityChange} />
      <AuditLogTable logs={logs} />
      {data && data.total > data.size && (
        <ListPagination total={data.total} noun="catatan" page={page} shownPage={data.page} lastPage={lastPage} onPageChange={onPageChange} />
      )}
    </PageTemplate>
  );
}
