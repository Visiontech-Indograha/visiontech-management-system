import { useState } from "react";
import { SurveysTemplate } from "@/components/templates/surveys/SurveysTemplate";
import { useSurveys, type SurveyState } from "@/services/surveyService";

/** Daftar survei ACS/CCTV. Semua dimuat sekali; tab menyaring di layar. Bawaan: yang menunggu tinjauan PM,
 * atau "Semua" bila tidak ada yang menunggu. */
export function SurveysPage() {
  const [picked, setPicked] = useState<SurveyState | "ALL" | null>(null);
  const query = useSurveys(undefined);
  const waiting = (query.data ?? []).some((s) => s.state === "SUBMITTED");
  const state = picked ?? (waiting ? "SUBMITTED" : "ALL");
  return <SurveysTemplate query={query} state={state === "ALL" ? undefined : state} onState={(s) => setPicked(s ?? "ALL")} />;
}
