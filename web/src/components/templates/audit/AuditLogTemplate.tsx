import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { LoadMoreBar } from "@/components/organisms/LoadMoreBar";
import type { KeysetMore } from "@/hooks/useKeysetList";
import { AuditFilterBar } from "@/components/organisms/audit/AuditFilterBar";
import type { ListControls } from "@/hooks/usePagedList";
import { AuditLogTable } from "@/components/organisms/audit/AuditLogTable";
import { AuditNavigationTabs } from "@/components/organisms/audit/AuditNavigationTabs";
import { BackupRegistryTable } from "@/components/organisms/audit/BackupRegistryTable";
import type { AuditEventList } from "@/services/auditService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka audit log: tab audit aktivitas vs backup basis data, saringan entitas, tabel catatan, halaman. */
export function AuditLogTemplate({ logs, more, controls, entity, dateFrom, dateTo, invalidRange }: {
  logs: UseQueryResult<AuditEventList>;
  more: KeysetMore;
  controls: ListControls;
  entity: string;
  dateFrom: string;
  dateTo: string;
  invalidRange: boolean;
}) {
  const [tab, setTab] = useState<"activity" | "backups">("activity");

  return (
    <PageTemplate title="Audit log">
      <AuditNavigationTabs activeTab={tab} onTabChange={setTab} />

      {tab === "activity" && (
        <div className="space-y-4">
          <AuditFilterBar controls={controls} entity={entity} dateFrom={dateFrom} dateTo={dateTo} invalidRange={invalidRange} />
          <AuditLogTable logs={logs} />
          <LoadMoreBar more={more} />
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
