import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useTransition, type WorkPlan } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Draft terarsip tidak dapat dibuka (GET /work-plans/{id} hanya rencana kerja aktif); pulihkan dari sini. */
export function PlanArchivedCard({ plan }: { plan: WorkPlan }) {
  const restore = useTransition(plan.id);
  const onRestore = async () => {
    try {
      await restore.mutateAsync({ action: "restore", row_version: plan.row_version });
      toast.success("Draf dipulihkan.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <div className="flex h-full flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
      <TextBlock as="span" className="font-medium">{plan.title}</TextBlock>
      <TextBlock className="text-sm text-mist">
        {plan.location_text} · {formatDate(plan.period_start)} – {formatDate(plan.period_end)}
      </TextBlock>
      <ActionButton variant="outline" onClick={onRestore} disabled={restore.isPending}>
        Pulihkan draf
      </ActionButton>
    </div>
  );
}
