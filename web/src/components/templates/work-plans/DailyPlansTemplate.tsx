import type { UseQueryResult } from "@tanstack/react-query";
import { DailyPlanDetailDialog } from "@/components/organisms/work-plans/DailyPlanDetailDialog";
import { DailyPlanFormDialog } from "@/components/organisms/work-plans/DailyPlanFormDialog";
import { DailyWeekMatrix, type MatrixTeam } from "@/components/organisms/work-plans/DailyWeekMatrix";
import { ApproveWeekButton, DailyWeekToolbar } from "@/components/organisms/work-plans/DailyWeekToolbar";
import type { DailyFormOptions, DailyPlan } from "@/services/dailyPlanService";
import { PageTemplate } from "../PageTemplate";

export type DailyDialog =
  | { kind: "create"; team_id: string; work_date: string }
  | { kind: "detail"; plan: DailyPlan }
  | { kind: "edit"; plan: DailyPlan }
  | null;

/** Kerangka "Jadwal harian": navigasi minggu, filter divisi, matriks tim × hari, persetujuan sekaligus. */
export function DailyPlansTemplate(props: {
  start: string;
  end: string;
  today: string;
  plans: UseQueryResult<DailyPlan[]>;
  options: DailyFormOptions | undefined;
  divisionId: string;
  canPlan: boolean;
  myEmployeeId: string | null;
  pendingApproval: number;
  approving: boolean;
  dialog: DailyDialog;
  onWeek: (delta: number | null) => void;
  onDivision: (id: string) => void;
  onApproveWeek: () => void;
  onDialog: (d: DailyDialog) => void;
}) {
  const { start, end, options, divisionId, canPlan, dialog, onDialog } = props;
  const teams: MatrixTeam[] = (options?.teams ?? []).filter((t) => !divisionId || t.division_id === divisionId);

  return (
    <PageTemplate
      title="Jadwal harian"
      action={
        canPlan && props.pendingApproval > 0 && (
          <ApproveWeekButton count={props.pendingApproval} busy={props.approving} onClick={props.onApproveWeek} />
        )
      }
    >
      <DailyWeekToolbar start={start} end={end} options={options} divisionId={divisionId}
                        onWeek={props.onWeek} onDivision={props.onDivision} />

      <DailyWeekMatrix
        plans={props.plans}
        teams={teams}
        start={start}
        today={props.today}
        canPlan={canPlan && !!options}
        onOpen={(plan) => onDialog({ kind: "detail", plan })}
        onCreate={(team, work_date) => onDialog({ kind: "create", team_id: team.team_id, work_date })}
      />

      {dialog?.kind === "create" && options && (
        <DailyPlanFormDialog options={options} initial={dialog} onClose={() => onDialog(null)} />
      )}
      {dialog?.kind === "edit" && options && (
        <DailyPlanFormDialog options={options} plan={dialog.plan} onClose={() => onDialog(null)} />
      )}
      {dialog?.kind === "detail" && (
        <DailyPlanDetailDialog
          plan={dialog.plan}
          canPlan={canPlan}
          isLeader={!!props.myEmployeeId && dialog.plan.leader_employee_id === props.myEmployeeId}
          onEdit={() => onDialog({ kind: "edit", plan: dialog.plan })}
          onClose={() => onDialog(null)}
        />
      )}
    </PageTemplate>
  );
}
