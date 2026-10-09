import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import { WorkPlansTemplate } from "@/components/templates/work-plans/WorkPlansTemplate";
import { useWorkPlans, type WorkPlan } from "@/services/workPlanService";

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
    <WorkPlansTemplate
      plans={plans}
      canManage={canManage}
      status={status}
      onStatusChange={setStatus}
      archived={archived}
      onArchivedChange={setArchived}
      preview={preview}
      onCreate={create}
      onEdit={setPreview}
      onClosePreview={() => setPreview(null)}
    />
  );
}
