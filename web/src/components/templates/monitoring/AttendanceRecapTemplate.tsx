import type { UseQueryResult } from "@tanstack/react-query";
import { AttendanceRecapSummary } from "@/components/organisms/monitoring/AttendanceRecapSummary";
import { AttendanceRecordHistory } from "@/components/organisms/monitoring/AttendanceRecordHistory";
import { MonthFilterField } from "@/components/organisms/monitoring/MonthFilterField";
import type { AttendanceRecap } from "@/services/monitoringService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Rekap absensi": saringan bulan, rekap per karyawan, riwayat jam masuk/keluar. */
export function AttendanceRecapTemplate({ month, onMonthChange, recap }: {
  month: string;
  onMonthChange: (month: string) => void;
  recap: UseQueryResult<AttendanceRecap>;
}) {
  const records = recap.data?.records ?? [];
  return (
    <PageTemplate title="Rekap bulanan">
      <div className="md:max-w-xs">
        <MonthFilterField value={month || recap.data?.month || ""} onChange={onMonthChange} hint="Kosong = bulan berjalan." />
      </div>
      <AttendanceRecapSummary recap={recap} />
      {records.length > 0 && <AttendanceRecordHistory records={records} />}
    </PageTemplate>
  );
}
