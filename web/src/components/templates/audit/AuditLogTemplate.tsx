import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { AuditEntityFilter } from "@/components/organisms/audit/AuditEntityFilter";
import { AuditLogTable } from "@/components/organisms/audit/AuditLogTable";
import { AuditNavigationTabs } from "@/components/organisms/audit/AuditNavigationTabs";
import { BackupRegistryTable } from "@/components/organisms/audit/BackupRegistryTable";
import type { AuditEventList } from "@/services/auditService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka audit log: tab audit aktivitas vs backup basis data, saringan entitas, tabel catatan, halaman. */
export function AuditLogTemplate({ logs, entity, onEntityChange, page, lastPage, onPageChange }: {
  logs: UseQueryResult<AuditEventList>;
  entity: string;
  onEntityChange: (entity: string) => void;
  page: number;
  lastPage: number;
  onPageChange: (page: number) => void;
}) {
  const [tab, setTab] = useState<"activity" | "backups">("activity");
  const data = logs.data;

  return (
    <PageTemplate title="Audit Log & Cadangan Sistem">
      <AuditNavigationTabs activeTab={tab} onTabChange={setTab} />

      {tab === "activity" && (
        <div className="space-y-4">
          <AuditEntityFilter entity={entity} onEntityChange={onEntityChange} />
          <AuditLogTable logs={logs} />
          {data && data.total > data.size && (
            <ListPagination total={data.total} noun="catatan" page={page} shownPage={data.page} lastPage={lastPage} onPageChange={onPageChange} />
          )}
        </div>
      )}

      {tab === "backups" && (
        <div className="pt-2">
          <BackupRegistryTable />
        </div>
      )}
    </PageTemplate>
  );
}
