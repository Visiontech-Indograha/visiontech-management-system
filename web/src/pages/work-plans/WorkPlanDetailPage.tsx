import { useParams } from "react-router-dom";
import { BackToPlansLink } from "@/components/organisms/work-plans/BackToPlansLink";
import { PlanStatusBadge } from "@/components/organisms/work-plans/PlanStatusBadge";
import { WorkPlanDetailBody } from "@/components/organisms/work-plans/WorkPlanDetailBody";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useActiveEmployees, useWorkPlan } from "@/services/workPlanService";

/** Detail rencana kerja (GET /work-plans/{id}); tindakan & panel mengikuti status dan kedudukan pengguna. */
export function WorkPlanDetailPage() {
  const { id = "" } = useParams();
  const plan = useWorkPlan(id);
  const employees = useActiveEmployees();
  const p = plan.data;

  return (
    <PageTemplate title={p?.title ?? "Work plan"} action={p && <PlanStatusBadge status={p.status} />}>
      <WorkPlanDetailBody plan={plan} employees={employees.data} />
      <BackToPlansLink />
    </PageTemplate>
  );
}
