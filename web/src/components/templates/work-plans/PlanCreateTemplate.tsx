import { PlanEditorV2Form } from "@/components/organisms/work-plans/PlanEditorV2Form";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Buat rencana kerja": form editor terintegrasi V2 (Weekly, Daily, Multi-Slot Items). */
export function PlanCreateTemplate() {
  return (
    <PageTemplate title="Buat Rencana Kerja Mingguan (V2)">
      <PlanEditorV2Form />
    </PageTemplate>
  );
}
