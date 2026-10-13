import { useParams } from "react-router-dom";
import { PresentationTemplate } from "@/components/templates/work-plans/PresentationTemplate";
import { useSessionIncidents } from "@/services/incidentService";
import { useFinalReport, usePlanAssets, usePlanTeam } from "@/services/reportService";
import { useWorkPlan } from "@/services/workPlanService";

/**
 * Mode presentasi laporan (M5, prototype/js/workplans.js `presentation`): hanya untuk rencana kerja yang sudah
 * selesai. Sampul → tim → hasil → insiden → lampiran → pengesahan. "Simpan PDF" memakai cetak peramban
 * (lanskap). Layar penuh, di luar AppShell.
 */
export function PresentationPage() {
  const { id = "" } = useParams();
  const plan = useWorkPlan(id);
  const completed = plan.data?.status === "COMPLETED";
  const team = usePlanTeam(id);
  const report = useFinalReport(id, completed);
  const incidents = useSessionIncidents(id);
  const assets = usePlanAssets(id, completed);

  return (
    <PresentationTemplate
      loading={plan.isPending || (completed && (team.isPending || report.isPending || incidents.isPending || assets.isPending))}
      plan={plan.data}
      completed={completed}
      report={report.data}
      team={team.data}
      incidents={incidents.data}
      assets={assets.data}
    />
  );
}
