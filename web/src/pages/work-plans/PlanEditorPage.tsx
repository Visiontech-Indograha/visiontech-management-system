import { useLocation, useParams, useSearchParams } from "react-router-dom";
import { PlanCreateTemplate } from "@/components/templates/work-plans/PlanCreateTemplate";
import { PlanEditTemplate } from "@/components/templates/work-plans/PlanEditTemplate";
import { usePlanDetail } from "@/services/workPlanService";

/** "Buat rencana kerja" (/work-plans/new), "Ubah isi" (/work-plans/:id/edit), dan "Revisi" (/:id/revise). */
export function PlanEditorPage() {
  const params = useParams();
  const [search] = useSearchParams();
  const revise = useLocation().pathname.endsWith("/revise") || Boolean(params.changeId);
  const changeId = params.changeId ?? search.get("change") ?? undefined;
  const id = params.id;
  const detail = usePlanDetail(id ?? "", Boolean(id));
  if (!id) return <PlanCreateTemplate />;
  const status = detail.data?.plan.status;
  const editable = revise ? ["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS"].includes(String(status)) : status === "DRAFT";
  return <PlanEditTemplate id={id} revise={revise} changeId={changeId} status={status} editable={editable} detail={detail} />;
}
