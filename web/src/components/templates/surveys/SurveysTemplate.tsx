import type { UseQueryResult } from "@tanstack/react-query";
import { SurveyList } from "@/components/organisms/surveys/SurveyList";
import { SurveyLogoPanel } from "@/components/organisms/surveys/SurveyLogoPanel";
import type { SurveyListItem, SurveyState } from "@/services/surveyService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka halaman daftar survei ACS/CCTV. */
export function SurveysTemplate(props: {
  query: UseQueryResult<SurveyListItem[]>;
  state: SurveyState | undefined;
  onState: (s: SurveyState | undefined) => void;
}) {
  return (
    <PageTemplate
      title="Survei"
      description="Survei lapangan ACS dan CCTV dari ketua tim: tinjau titik dan foto, lihat pratinjau laporan, setujui, unduh dokumen resmi, lalu rencanakan pemasangan."
    >
      <div className="space-y-4">
        <SurveyLogoPanel />
        <SurveyList {...props} />
      </div>
    </PageTemplate>
  );
}
