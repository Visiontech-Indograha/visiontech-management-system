import { useState } from "react";
import { AttendanceRecapSummary } from "@/components/organisms/monitoring/AttendanceRecapSummary";
import { AttendanceRecordHistory } from "@/components/organisms/monitoring/AttendanceRecordHistory";
import { MonthFilterField } from "@/components/organisms/monitoring/MonthFilterField";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useAttendanceRecap } from "@/services/monitoringService";

/** Rekap absensi per karyawan per bulan (GET /recaps/attendance). Cakupan data ditentukan API (R-33:
 * Finance & OPS semua, PM bawahannya, lainnya milik sendiri) + riwayat jam masuk & keluar. */
export function AttendanceRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useAttendanceRecap(month);
  const records = recap.data?.records ?? [];

  return (
    <PageTemplate title="Rekap absensi">
      <div className="md:max-w-xs">
        <MonthFilterField value={month || recap.data?.month || ""} onChange={setMonth} hint="Kosong = bulan berjalan." />
      </div>
      <AttendanceRecapSummary recap={recap} />
      {records.length > 0 && <AttendanceRecordHistory records={records} />}
    </PageTemplate>
  );
}
