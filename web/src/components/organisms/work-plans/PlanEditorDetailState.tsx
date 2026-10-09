import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import type { PlanDetail } from "@/services/workPlanService";
import { PlanEditorForm } from "./PlanEditorForm";

/** Memuat rencana kerja yang diedit; form hanya tampil bila statusnya masih boleh diubah. */
export function PlanEditorDetailState({ detail, editable, planId, revise, changeId }: {
  detail: UseQueryResult<PlanDetail>;
  editable: boolean;
  planId: string;
  revise: boolean;
  changeId: string | undefined;
}) {
  return (
      <QueryState query={detail} errorText="Rencana Kerja tidak ditemukan atau Anda tidak berwenang mengubahnya.">
        {detail.data &&
          (editable ? (
            <PlanEditorForm planId={planId} detail={detail.data} revise={revise} changeId={changeId} />
          ) : (
            <p className="text-sm text-mist">Isi rencana kerja tidak dapat diubah pada tahap ini.</p>
          ))}
      </QueryState>
  );
}
