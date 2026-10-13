import { useState } from "react";
import { AttendanceRecapTemplate } from "@/components/templates/monitoring/AttendanceRecapTemplate";
import { useAttendanceRecap } from "@/services/monitoringService";


/** Rekap absensi per karyawan per bulan (GET /recaps/attendance). Cakupan data ditentukan API (R-33:
 * Finance & OPS semua, PM bawahannya, lainnya milik sendiri) + riwayat jam masuk & keluar. */
export function AttendanceRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useAttendanceRecap(month);
  return <AttendanceRecapTemplate month={month} onMonthChange={setMonth} recap={recap} />;
}
