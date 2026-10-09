import { useLocation, useParams, useSearchParams } from "react-router-dom";
import { PlanEditorDetailState } from "@/components/organisms/work-plans/PlanEditorDetailState";
import { PlanEditorForm } from "@/components/organisms/work-plans/PlanEditorForm";
import { PlanPendingRequests } from "@/components/organisms/work-plans/PlanPendingRequests";
import { PlanReviseNotice } from "@/components/organisms/work-plans/PlanReviseNotice";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { usePlanDetail } from "@/services/workPlanService";

/** "Buat rencana kerja" (/work-plans/new), "Ubah isi" (/work-plans/:id/edit), dan "Revisi" (/:id/revise). */
export function PlanEditorPage() {
  const params = useParams();
  const [search] = useSearchParams();
  const revise = useLocation().pathname.endsWith("/revise") || Boolean(params.changeId);
  const changeId = params.changeId ?? search.get("change") ?? undefined;
  const id = params.id;
  const detail = usePlanDetail(id ?? "", Boolean(id));
  if (!id)
    return (
      <PageTemplate title="Buat rencana kerja">
        <PlanEditorForm />
      </PageTemplate>
    );
  const status = detail.data?.plan.status;
  const editable = revise ? ["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS"].includes(String(status)) : status === "DRAFT";
  return (
    <PageTemplate title={revise ? "Revisi rencana kerja" : "Ubah isi rencana kerja"}>
      {revise && <PlanReviseNotice status={status} />}
      {revise && <PlanPendingRequests planId={id} />}
      <PlanEditorDetailState detail={detail} editable={editable} planId={id} revise={revise} changeId={changeId} />
    </PageTemplate>
  );
}
