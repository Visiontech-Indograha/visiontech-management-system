import type { UseQueryResult } from "@tanstack/react-query";
import { SurveyBomPanel } from "@/components/organisms/surveys/SurveyBomPanel";
import { SurveyLayoutMap } from "@/components/organisms/surveys/SurveyLayoutMap";
import { SurveyLoadState } from "@/components/organisms/surveys/SurveyLoadState";
import { SurveyPlanDialog } from "@/components/organisms/surveys/SurveyPlanDialog";
import { SurveyPointsPanel } from "@/components/organisms/surveys/SurveyPointsPanel";
import { SurveyPreviewPanel } from "@/components/organisms/surveys/SurveyPreviewPanel";
import { SurveyReviewBar } from "@/components/organisms/surveys/SurveyReviewBar";
import { SurveySummary } from "@/components/organisms/surveys/SurveySummary";
import { SurveyTabs } from "@/components/organisms/surveys/SurveyTabs";
import type { Survey } from "@/services/surveyService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka detail survei: ringkasan + aksi PM, lalu tab Titik & foto / Pratinjau laporan / Bill of Material. */
export function SurveyDetailTemplate({ query, planning, onPlan, onClosePlan }: {
  query: UseQueryResult<Survey>;
  planning: boolean;
  onPlan: () => void;
  onClosePlan: () => void;
}) {
  const s = query.data;
  return (
    <PageTemplate
      title={s ? `Survei ${s.format} — ${s.client_name}` : "Survei"}
      description={s ? `${s.project_title} · ${s.location ?? "-"}` : undefined}
      action={s && <SurveyReviewBar survey={s} onPlan={onPlan} />}
    >
      <SurveyLoadState query={query}>
        {(s) => (
          <>
            <SurveySummary survey={s} />
            <SurveyTabs
              points={<SurveyPointsPanel survey={s} />}
              map={<SurveyLayoutMap survey={s} />}
              preview={<SurveyPreviewPanel taskId={s.task_id} version={`${s.state}-${s.points.map((p) => `${p.site_lat},${p.site_lng}`).join("|")}`} />}
              bom={<SurveyBomPanel survey={s} />}
            />
            {planning && <SurveyPlanDialog survey={s} onClose={onClosePlan} />}
          </>
        )}
      </SurveyLoadState>
    </PageTemplate>
  );
}
