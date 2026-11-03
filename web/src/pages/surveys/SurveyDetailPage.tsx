import { useState } from "react";
import { useParams } from "react-router-dom";
import { SurveyDetailTemplate } from "@/components/templates/surveys/SurveyDetailTemplate";
import { useSurvey } from "@/services/surveyService";

/** Detail survei: titik & foto, pratinjau laporan, BoM, aksi PM. */
export function SurveyDetailPage() {
  const { id, surveyId } = useParams<{ id?: string; surveyId?: string }>();
  const targetId = surveyId || id || "";
  const query = useSurvey(targetId);
  const [planning, setPlanning] = useState(false);
  return (
    <SurveyDetailTemplate
      query={query}
      planning={planning}
      onPlan={() => setPlanning(true)}
      onClosePlan={() => setPlanning(false)}
    />
  );
}
