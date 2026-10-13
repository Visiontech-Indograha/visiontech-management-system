import type { UseQueryResult } from "@tanstack/react-query";
import { PlanEditorDetailState } from "@/components/organisms/work-plans/PlanEditorDetailState";
import { PlanPendingRequests } from "@/components/organisms/work-plans/PlanPendingRequests";
import { PlanReviseNotice } from "@/components/organisms/work-plans/PlanReviseNotice";
import type { PlanDetail } from "@/services/workPlanService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Ubah isi" / "Revisi rencana kerja": pemberitahuan revisi, permintaan ketua, form editor. */
export function PlanEditTemplate({ id, revise, changeId, status, editable, detail }: {
  id: string;
  revise: boolean;
  changeId: string | undefined;
  status: unknown;
  editable: boolean;
  detail: UseQueryResult<PlanDetail>;
}) {
  return (
    <PageTemplate title={revise ? "Revisi rencana kerja" : "Ubah isi rencana kerja"}>
      {revise && <PlanReviseNotice status={status} />}
      {revise && <PlanPendingRequests planId={id} />}
      <PlanEditorDetailState detail={detail} editable={editable} planId={id} revise={revise} changeId={changeId} />
    </PageTemplate>
  );
}
