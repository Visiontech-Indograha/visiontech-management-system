import { STATUS_LABEL } from "@/lib/labels";
import { ControlInput, ControlLabel, ControlOption, ControlSelect } from "@/components/molecules/FormBlock";

const PLAN_STATUSES = ["DRAFT", "PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED", "CANCELLED"];
const selectCls = "h-11 w-full rounded-control border border-line bg-surface px-3 text-sm md:w-auto";

/** Saring daftar rencana kerja: status + (pengelola) draf terarsip. */
export function PlanListFilter({ status, onStatusChange, archived, onArchivedChange, canManage }: {
  status: string;
  onStatusChange: (status: string) => void;
  archived: boolean;
  onArchivedChange: (archived: boolean) => void;
  canManage: boolean;
}) {
  return (
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
        <ControlSelect aria-label="Filter status" className={selectCls} value={status} onChange={(e) => onStatusChange(e.target.value)}>
          <ControlOption value="">Semua status</ControlOption>
          {PLAN_STATUSES.map((s) => (
            <ControlOption key={s} value={s}>
              {STATUS_LABEL[s]}
            </ControlOption>
          ))}
        </ControlSelect>
        {canManage && (
          <ControlLabel className="flex min-h-11 items-center gap-2 text-sm">
            <ControlInput type="checkbox" className="size-5" checked={archived} onChange={(e) => onArchivedChange(e.target.checked)} />
            Tampilkan draf terarsip
          </ControlLabel>
        )}
      </div>
  );
}
