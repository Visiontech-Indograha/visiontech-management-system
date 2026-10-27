import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { CorrectionsPanel } from "@/components/organisms/work-plans/CorrectionsPanel";
import { WeeklyPresentationDialog } from "@/components/organisms/work-plans/WeeklyPresentationDialog";
import { DailyPlanDetailDialog } from "@/components/organisms/work-plans/DailyPlanDetailDialog";
import { DailyPlanFormDialog } from "@/components/organisms/work-plans/DailyPlanFormDialog";
import { DailyWeekMatrix, type MatrixTeam } from "@/components/organisms/work-plans/DailyWeekMatrix";
import { ApproveWeekButton, DailyWeekToolbar, WeekRecapButtons } from "@/components/organisms/work-plans/DailyWeekToolbar";
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
  const [presentationOpen, setPresentationOpen] = useState(false);
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
      {canPlan && options && (
        <div className="mb-4">
          <WeekRecapButtons
            divisionId={divisionId || (options.divisions.length === 1 ? options.divisions[0]!.division_id : "")}
            start={start}
            end={end}
            onOpenPresentation={() => setPresentationOpen(true)}
          />
        </div>
      )}

      <DailyWeekMatrix
        divisionId={divisionId}
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
      {presentationOpen && options && (
        <WeeklyPresentationDialog
          open={presentationOpen}
          onClose={() => setPresentationOpen(false)}
          teams={teams}
          initialDate={props.end}
        />
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
      <CorrectionsPanel canDecide={canPlan} />
    </PageTemplate>
  );
}
