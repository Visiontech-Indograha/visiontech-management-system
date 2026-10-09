import type { UseQueryResult } from "@tanstack/react-query";
import { BackToPlansLink } from "@/components/organisms/work-plans/BackToPlansLink";
import { PlanStatusBadge } from "@/components/organisms/work-plans/PlanStatusBadge";
import { WorkPlanDetailBody } from "@/components/organisms/work-plans/WorkPlanDetailBody";
import type { employeeName, WorkPlan } from "@/services/workPlanService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka detail rencana kerja: judul + status, isi sesuai status, tautan kembali. */
export function WorkPlanDetailTemplate({ plan, employees }: {
  plan: UseQueryResult<WorkPlan>;
  employees: Parameters<typeof employeeName>[0];
}) {
  const p = plan.data;
  return (
    <PageTemplate title={p?.title ?? "Work plan"} action={p && <PlanStatusBadge status={p.status} />}>
      <WorkPlanDetailBody plan={plan} employees={employees} />
      <BackToPlansLink />
    </PageTemplate>
  );
}
