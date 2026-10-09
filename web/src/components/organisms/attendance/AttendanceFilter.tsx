import { TextField } from "@/components/molecules/Field";
import { STATUS_LABEL } from "@/lib/labels";
import type { AttendanceFilters } from "@/services/attendanceService";

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
          <label htmlFor="att-status" className="text-sm font-medium">
            Status
          </label>
          <select id="att-status" className={selectCls} value={f.status} onChange={(e) => set({ status: e.target.value })}>
            <option value="">Semua status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
        <TextField label="Dari tanggal" type="date" value={f.from} onChange={(e) => set({ from: e.target.value })} />
        <TextField label="Sampai tanggal" type="date" value={f.to} onChange={(e) => set({ to: e.target.value })} />
      </div>
  );
}
