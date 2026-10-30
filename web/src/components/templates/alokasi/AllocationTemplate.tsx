import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { ActivateStandbyDialog } from "@/components/organisms/alokasi/ActivateStandbyDialog";
import { AllocBoard } from "@/components/organisms/alokasi/AllocBoard";
import { AllocToolbar } from "@/components/organisms/alokasi/AllocToolbar";
import { AllocateDialog, type AllocCell } from "@/components/organisms/alokasi/AllocateDialog";
import { CopyWeekConfirmDialog, StandbyConfirmDialog } from "@/components/organisms/alokasi/WeekConfirmDialogs";
import {
  cellKey,
  cellKind,
  emptyCells,
  standbyGroups,
  type WeeklyCell,
  type WeeklyMatrix,
  type WeeklyRow,
} from "@/lib/alokasi";
import type { DailyFormOptions } from "@/services/dailyPlanService";
import { addDays } from "@/services/dailyPlanService";

export type AllocDialog =
  | { kind: "allocate"; divisionId: string; cells: AllocCell[] }
  | { kind: "standby" }
  | { kind: "copy" }
  | { kind: "activate"; divisionId: string; plan: { daily_plan_id: string; team_name: string; work_date: string } }
  | null;

/** Kerangka "Alokasi mingguan" (PM/OM): bilah aksi, papan matriks, dan dialog. Pilihan sel disimpan di sini. */
export function AllocationTemplate(props: {
  start: string;
  today: string;
  matrix: UseQueryResult<WeeklyMatrix>;
  options: DailyFormOptions | undefined;
  divisionId: string;
  onWeek: (delta: number | null) => void;
  onDivision: (id: string) => void;
}) {
  const { start, today, matrix, options, divisionId } = props;
  const end = addDays(start, 6);
  const [multi, setMulti] = useState(false);
  const [selected, setSelected] = useState<Map<string, AllocCell>>(new Map());
  const [selDivision, setSelDivision] = useState<string | null>(null);
  const [dialog, setDialog] = useState<AllocDialog>(null);
  const data = matrix.data;
  const standbyCount = data ? emptyCells(data, today).length : 0;

  const rowsOf = (divId: string | null): WeeklyRow[] => (data?.rows ?? []).filter((r) => !divId || r.division_id === divId);
  const clearSelection = () => {
    setSelected(new Map());
    setSelDivision(null);
  };

  const onCell = (row: WeeklyRow, cell: WeeklyCell) => {
    const kind = cellKind(cell);
    const future = cell.work_date >= today;
    if (multi) {
      if (kind !== "EMPTY" || !future) return;
      const key = cellKey(row.team_id, cell.work_date);
      const next = new Map(selDivision === row.division_id ? selected : []);
      if (next.has(key)) next.delete(key);
      else next.set(key, { team_id: row.team_id, work_date: cell.work_date });
      setSelected(next);
      setSelDivision(next.size ? row.division_id : null);
      return;
    }
    if (kind === "EMPTY" && future) {
      setDialog({ kind: "allocate", divisionId: row.division_id, cells: [{ team_id: row.team_id, work_date: cell.work_date }] });
    } else if (kind === "STANDBY" && future && cell.daily_plan_id) {
      setDialog({
        kind: "activate",
        divisionId: row.division_id,
        plan: { daily_plan_id: cell.daily_plan_id, team_name: row.team_name, work_date: cell.work_date },
      });
    }
  };

  return (
    <PageTemplate title="Alokasi mingguan">
      <AllocToolbar
        start={start}
        end={end}
        divisions={options?.divisions ?? []}
        divisionId={divisionId}
        multi={multi}
        selectedCount={selected.size}
        standbyCount={standbyCount}
        copyEnabled={!!data && data.rows.some((r) => r.cells.some((c) => c.daily_plan_id))}
        onWeek={props.onWeek}
        onDivision={props.onDivision}
        onToggleMulti={() => {
          setMulti((m) => !m);
          clearSelection();
        }}
        onClearSelection={clearSelection}
        onAllocate={() => selDivision && setDialog({ kind: "allocate", divisionId: selDivision, cells: [...selected.values()] })}
        onStandby={() => setDialog({ kind: "standby" })}
        onCopy={() => setDialog({ kind: "copy" })}
      />

      <AllocBoard
        query={matrix}
        today={today}
        selected={new Set(selected.keys())}
        multi={multi}
        onCell={onCell}
      />

      {dialog?.kind === "allocate" && options && (
        <AllocateDialog
          divisionId={dialog.divisionId}
          cells={dialog.cells}
          teams={rowsOf(dialog.divisionId)}
          orders={options.orders}
          today={today}
          onClose={() => {
            setDialog(null);
            clearSelection();
          }}
        />
      )}
      {dialog?.kind === "standby" && (
        <StandbyConfirmDialog groups={data ? standbyGroups(data, today) : []} cellCount={standbyCount}
                              onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === "copy" && data && <CopyWeekConfirmDialog matrix={data} onClose={() => setDialog(null)} />}
      {dialog?.kind === "activate" && options && (
        <ActivateStandbyDialog plan={dialog.plan} divisionId={dialog.divisionId} orders={options.orders}
                               onClose={() => setDialog(null)} />
      )}
    </PageTemplate>
  );
}
