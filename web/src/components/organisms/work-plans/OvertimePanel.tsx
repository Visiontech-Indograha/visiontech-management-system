import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import { employeeName, useActiveEmployees, type WorkPlan } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { type Overtime, useOvertime } from "@/services/overtimeService";
import { OvertimeReviewDialog } from "@/components/organisms/work-plans/OvertimeReviewDialog";
import { SectionTitle } from "@/components/molecules/SectionTitle";

/** Panel "Rekap Lembur" per rencana kerja (GET /overtime?work_plan_id); PM (create:plan) meninjau yang PENDING_PM. */
export function OvertimePanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canReview = !!me?.permissions.includes("create:plan");
  const list = useOvertime(plan.id);
  const employees = useActiveEmployees();
  const [reviewing, setReviewing] = useState<Overtime | null>(null);
  if (list.data?.length === 0) return null;
  return (
    <section aria-label="Rekap Lembur" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <SectionTitle>Rekap Lembur</SectionTitle>
      <QueryState query={list} errorText="Data lembur tidak dapat dimuat.">
        <ListBlock className="space-y-3">
          {list.data?.map((o) => (
            <ListEntry key={o.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
              <div className="flex items-start justify-between gap-2">
                <TextBlock as="strong" className="text-sm">{employeeName(employees.data, o.employee_id)}</TextBlock>
                <StatusBadge status={o.status} />
              </div>
              <TextBlock className="text-sm">
                {o.hours} jam · {o.reason}
              </TextBlock>
              <TextBlock className="text-xs text-mist">
                {formatDate(o.work_date)}
                {o.review_note ? ` · ${o.review_note}` : ""}
              </TextBlock>
              {canReview && o.status === "PENDING_PM" && (
                <ActionButton size="sm" className="mt-2" onClick={() => setReviewing(o)}>
                  Tinjau lembur
                </ActionButton>
              )}
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
      {reviewing && <OvertimeReviewDialog plan={plan} item={reviewing} onClose={() => setReviewing(null)} />}
    </section>
  );
}

