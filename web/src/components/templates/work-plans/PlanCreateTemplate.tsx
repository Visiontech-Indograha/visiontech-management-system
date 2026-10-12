import { PlanEditorForm } from "@/components/organisms/work-plans/PlanEditorForm";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Buat rencana kerja": form editor kosong. */
export function PlanCreateTemplate() {
  return (
      <PageTemplate title="Buat rencana kerja">
        <PlanEditorForm />
      </PageTemplate>
  );
}
