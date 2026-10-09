import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "@/app/session";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useWorkPlans, type WorkPlan } from "@/services/workPlanService";
import { PlanCreateButton } from "@/components/organisms/work-plans/PlanCreateButton";
import { PlanList } from "@/components/organisms/work-plans/PlanList";
import { PlanListFilter } from "@/components/organisms/work-plans/PlanListFilter";
import { PlanPreviewDialog } from "@/components/organisms/work-plans/PlanPreviewDialog";

/** Daftar rencana kerja yang terlihat oleh pengguna (GET /work-plans; API menyaring sesuai kedudukan). */
export function WorkPlansPage() {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const [status, setStatus] = useState("");
  const [archived, setArchived] = useState(false);
  const navigate = useNavigate();
  const [preview, setPreview] = useState<WorkPlan | null>(null);
  const create = () => navigate("/work-plans/new");
  const plans = useWorkPlans({ status, archived });

  return (
    <PageTemplate title="Rencana Kerja" action={canManage && <PlanCreateButton onCreate={create} />}>
      <PlanListFilter
        status={status}
        onStatusChange={setStatus}
        archived={archived}
        onArchivedChange={setArchived}
        canManage={canManage}
      />
      <PlanList plans={plans} archived={archived} canManage={canManage} onCreate={create} onEdit={setPreview} />
      {preview && (
        <PlanPreviewDialog
          title={`Sunting rencana kerja — ${preview.title}`}
          path={`/work-plans/${preview.id}/preview`}
          editTo={`/work-plans/${preview.id}/edit`}
          onClose={() => setPreview(null)}
        />
      )}
    </PageTemplate>
  );
}
