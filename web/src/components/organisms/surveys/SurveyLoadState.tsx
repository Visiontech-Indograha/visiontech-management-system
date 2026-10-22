import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { QueryState } from "@/components/molecules/QueryState";
import type { Survey } from "@/services/surveyService";

/** Keadaan memuat / galat detail survei; isi dirender setelah data ada. */
export function SurveyLoadState({ query, children }: {
  query: UseQueryResult<Survey>;
  children: (survey: Survey) => ReactNode;
}) {
  return (
    <QueryState query={query} errorText="Survei tidak dapat dimuat atau Anda tidak berhak membukanya.">
      {query.data ? children(query.data) : null}
    </QueryState>
  );
}
