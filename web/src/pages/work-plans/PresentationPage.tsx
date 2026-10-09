import { useParams } from "react-router-dom";
import { PlanPresentationSlides } from "@/components/organisms/work-plans/PlanPresentationSlides";
import { PresentationSkeleton } from "@/components/organisms/work-plans/PresentationSkeleton";
import { PresentationToolbar } from "@/components/organisms/work-plans/PresentationToolbar";
import { PresentationUnavailable } from "@/components/organisms/work-plans/PresentationUnavailable";
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
  const p = plan.data;
  const r = report.data;

  if (plan.isPending || (completed && (team.isPending || report.isPending || incidents.isPending || assets.isPending)))
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-6">
        <PresentationSkeleton />
      </main>
    );
  if (!p || !completed || !r)
    return (
      <main className="mx-auto max-w-xl p-6 text-center">
        <PresentationUnavailable backTo={p ? `/work-plans/${p.id}` : "/work-plans"} />
      </main>
    );

  return (
    <main className="h-dvh snap-y snap-mandatory overflow-y-auto bg-ink/5 print:h-auto print:overflow-visible">
      <PresentationToolbar planId={p.id} />
      <PlanPresentationSlides plan={p} report={r} team={team.data} incidents={incidents.data} assets={assets.data} />
    </main>
  );
}
