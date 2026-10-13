import type { UseQueryResult } from "@tanstack/react-query";
import { PlanCreateButton } from "@/components/organisms/work-plans/PlanCreateButton";
import { PlanList } from "@/components/organisms/work-plans/PlanList";
import { PlanListFilter } from "@/components/organisms/work-plans/PlanListFilter";
import { PlanPreviewDialog } from "@/components/organisms/work-plans/PlanPreviewDialog";
import type { WorkPlan } from "@/services/workPlanService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka daftar rencana kerja: saringan, kartu rencana, pratinjau draf. */
export function WorkPlansTemplate({ plans, canManage, status, onStatusChange, archived, onArchivedChange, preview, onCreate, onEdit, onClosePreview }: {
  plans: UseQueryResult<WorkPlan[]>;
  canManage: boolean;
  status: string;
  onStatusChange: (status: string) => void;
  archived: boolean;
  onArchivedChange: (archived: boolean) => void;
  preview: WorkPlan | null;
  onCreate: () => void;
  onEdit: (plan: WorkPlan) => void;
  onClosePreview: () => void;
}) {
  return (
    <PageTemplate title="Rencana Kerja" action={canManage && <PlanCreateButton onCreate={onCreate} />}>
      <PlanListFilter
        status={status}
        onStatusChange={onStatusChange}
        archived={archived}
        onArchivedChange={onArchivedChange}
        canManage={canManage}
      />
      <PlanList plans={plans} archived={archived} canManage={canManage} onCreate={onCreate} onEdit={onEdit} />
      {preview && (
        <PlanPreviewDialog
          title={`Sunting rencana kerja — ${preview.title}`}
          path={`/work-plans/${preview.id}/preview`}
          editTo={`/work-plans/${preview.id}/edit`}
          onClose={onClosePreview}
        />
      )}
    </PageTemplate>
  );
}
