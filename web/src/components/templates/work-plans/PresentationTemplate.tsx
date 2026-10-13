import { PlanPresentationSlides } from "@/components/organisms/work-plans/PlanPresentationSlides";
import { PresentationSkeleton } from "@/components/organisms/work-plans/PresentationSkeleton";
import { PresentationToolbar } from "@/components/organisms/work-plans/PresentationToolbar";
import { PresentationUnavailable } from "@/components/organisms/work-plans/PresentationUnavailable";
import type { Incident } from "@/services/incidentService";
import type { FinalReport, PlanAsset, TeamMember } from "@/services/reportService";
import type { WorkPlan } from "@/services/workPlanService";

/** Kerangka mode presentasi layar penuh: memuat → tidak tersedia → slide + bilah tombol. */
export function PresentationTemplate({ loading, plan: p, completed, report: r, team, incidents, assets }: {
  loading: boolean;
  plan: WorkPlan | undefined;
  completed: boolean;
  report: FinalReport | null | undefined;
  team: TeamMember[] | undefined;
  incidents: Incident[] | undefined;
  assets: PlanAsset[] | undefined;
}) {
  if (loading)
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
      <PlanPresentationSlides plan={p} report={r} team={team} incidents={incidents} assets={assets} />
    </main>
  );
}
