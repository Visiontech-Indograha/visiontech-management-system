import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import type { employeeName, WorkPlan } from "@/services/workPlanService";
import { DailyReportsPanel } from "./DailyReportsPanel";
import { FinalReportPanel } from "./FinalReportPanel";
import { PlanActionsPanel } from "./PlanActionsPanel";
import { PlanAttachmentsPanel } from "./PlanAttachmentsPanel";
import { PlanDetailCard } from "./PlanDetailCard";
import { PlanDocumentsPanel } from "./PlanDocumentsPanel";
import { PlanLocationCard } from "./PlanLocationCard";
import { PlanSummaryCard } from "./PlanSummaryCard";
import { WeeklyReportsPanel } from "./WeeklyReportsPanel";

/** Isi halaman detail rencana kerja sesuai status: rincian + tindakan, tim, laporan akhir, lokasi, lampiran, dokumen, laporan. */
export function WorkPlanDetailBody({ plan, employees }: {
  plan: UseQueryResult<WorkPlan>;
  employees: Parameters<typeof employeeName>[0];
}) {
  const p = plan.data;
  return (
      <QueryState query={plan} errorText="Work plan tidak ditemukan atau Anda tidak berwenang melihatnya.">
        {p && (
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <PlanSummaryCard plan={p} employees={employees} />
            <PlanActionsPanel plan={p} />
          </div>
        )}
        {p && <PlanDetailCard plan={p} />}
        {p && ["IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED"].includes(p.status) && <FinalReportPanel plan={p} />}
        {p && <PlanLocationCard plan={p} />}
        {p && <PlanAttachmentsPanel plan={p} />}
        {p && p.status !== "DRAFT" && <PlanDocumentsPanel plan={p} />}
        {p && ["IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED"].includes(p.status) && (
          <div className="mt-6 space-y-6">
            <DailyReportsPanel plan={p} />
            <WeeklyReportsPanel plan={p} />
          </div>
        )}
      </QueryState>
  );
}
