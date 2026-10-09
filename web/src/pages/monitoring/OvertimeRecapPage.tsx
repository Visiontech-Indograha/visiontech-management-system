import { useState } from "react";
import { OvertimeRecapTemplate } from "@/components/templates/monitoring/OvertimeRecapTemplate";
import { useOvertimeRecap } from "@/services/monitoringService";

/** "Rekap lembur" per karyawan per bulan (GET /recaps/overtime). Cakupan: Finance/OPS/Admin semua, PM unitnya. */
export function OvertimeRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useOvertimeRecap(month);
  return <OvertimeRecapTemplate month={month} onMonthChange={setMonth} recap={recap} />;
}
