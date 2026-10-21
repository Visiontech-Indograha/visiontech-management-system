import { useState } from "react";
import { SurveysTemplate } from "@/components/templates/surveys/SurveysTemplate";
import { useSurveys, type SurveyState } from "@/services/surveyService";

/** Daftar survei ACS/CCTV; bawaan menampilkan yang menunggu tinjauan PM. */
export function SurveysPage() {
  const [state, setState] = useState<SurveyState | undefined>("SUBMITTED");
  const query = useSurveys(state);
  return <SurveysTemplate query={query} state={state} onState={setState} />;
}
