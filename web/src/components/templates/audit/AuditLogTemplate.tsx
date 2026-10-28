import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ListPagination } from "@/components/organisms/ListPagination";
import { AuditFilterBar } from "@/components/organisms/audit/AuditFilterBar";
import type { ListControls } from "@/hooks/usePagedList";
import { AuditLogTable } from "@/components/organisms/audit/AuditLogTable";
import { AuditNavigationTabs } from "@/components/organisms/audit/AuditNavigationTabs";
import { BackupRegistryTable } from "@/components/organisms/audit/BackupRegistryTable";
import type { AuditEventList } from "@/services/auditService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka audit log: tab audit aktivitas vs backup basis data, saringan entitas, tabel catatan, halaman. */
export function AuditLogTemplate({ logs, controls, entity, dateFrom, dateTo, invalidRange, lastPage }: {
  logs: UseQueryResult<AuditEventList>;
  controls: ListControls;
  entity: string;
  dateFrom: string;
  dateTo: string;
  invalidRange: boolean;
  lastPage: number;
}) {
  const [tab, setTab] = useState<"activity" | "backups">("activity");
  const data = logs.data;

  return (
    <PageTemplate title="Audit Log & Cadangan Sistem">
      <AuditNavigationTabs activeTab={tab} onTabChange={setTab} />

      {tab === "activity" && (
        <div className="space-y-4">
          <AuditFilterBar controls={controls} entity={entity} dateFrom={dateFrom} dateTo={dateTo} invalidRange={invalidRange} />
          <AuditLogTable logs={logs} />
          {data && data.total > data.size && (
            <ListPagination total={data.total} noun="catatan" page={controls.page} shownPage={data.page} lastPage={lastPage} onPageChange={controls.setPage} />
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
