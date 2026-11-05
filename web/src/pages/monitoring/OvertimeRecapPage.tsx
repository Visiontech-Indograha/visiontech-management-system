import { useState } from "react";
import { OvertimeRecapTemplate } from "@/components/templates/monitoring/OvertimeRecapTemplate";
import { useOvertimeRecap } from "@/services/monitoringService";
import { useOvertimePending } from "@/services/overtimeService";

/** "Rekap lembur": antrean tinjau (GET /overtime?status=PENDING_PM) dan rekap per karyawan per bulan
 * (GET /recaps/overtime). Cakupan: Finance/OPS/Admin semua, PM unitnya. */
export function OvertimeRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useOvertimeRecap(month);
  const { query: pending, more } = useOvertimePending();
  return <OvertimeRecapTemplate month={month} onMonthChange={setMonth} recap={recap} pending={pending} more={more} />;
}
