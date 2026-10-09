import { TextField } from "@/components/molecules/Field";
import { STATUS_LABEL } from "@/lib/labels";
import type { AttendanceFilters } from "@/services/attendanceService";
import { ControlLabel, ControlOption, ControlSelect } from "@/components/molecules/FormBlock";

const STATUSES = ["NEEDS_REVIEW", "AUTO_VALID", "APPROVED", "REJECTED"];
const selectCls = "h-11 w-full rounded-control border border-line bg-surface px-3 text-sm";

/** Saring absensi: status + rentang tanggal. Mengubah saringan kembali ke halaman 1 (diatur Page). */
export function AttendanceFilter({ filters: f, onChange: set }: {
  filters: AttendanceFilters;
  onChange: (patch: Partial<AttendanceFilters>) => void;
}) {
  return (
      <div className="mb-4 grid gap-x-3 md:grid-cols-3">
        <div className="mb-4 space-y-1.5">
          <ControlLabel htmlFor="att-status" className="text-sm font-medium">
            Status
          </ControlLabel>
          <ControlSelect id="att-status" className={selectCls} value={f.status} onChange={(e) => set({ status: e.target.value })}>
            <ControlOption value="">Semua status</ControlOption>
            {STATUSES.map((s) => (
              <ControlOption key={s} value={s}>
                {STATUS_LABEL[s]}
              </ControlOption>
            ))}
          </ControlSelect>
        </div>
        <TextField label="Dari tanggal" type="date" value={f.from} onChange={(e) => set({ from: e.target.value })} />
        <TextField label="Sampai tanggal" type="date" value={f.to} onChange={(e) => set({ to: e.target.value })} />
      </div>
  );
}
