import { useParams } from "react-router-dom";
import { WorkPlanDetailTemplate } from "@/components/templates/work-plans/WorkPlanDetailTemplate";
import { useActiveEmployees, useWorkPlan } from "@/services/workPlanService";

/** Detail rencana kerja (GET /work-plans/{id}); tindakan & panel mengikuti status dan kedudukan pengguna. */
export function WorkPlanDetailPage() {
  const { id = "" } = useParams();
  const plan = useWorkPlan(id);
  const employees = useActiveEmployees();
  return <WorkPlanDetailTemplate plan={plan} employees={employees.data} />;
}
