import { useState } from "react";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { MonthFilterField } from "../components/MonthFilterField";
import { OvertimeRecapList } from "../components/OvertimeRecapList";
import { useOvertimeRecap } from "../monitoringService";

/** "Rekap lembur" per karyawan per bulan (GET /recaps/overtime). Cakupan: Finance/OPS/Admin semua, PM unitnya. */
export function OvertimeRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useOvertimeRecap(month);
  return (
    <PageTemplate title="Rekap lembur">
      <div className="md:max-w-xs">
        <MonthFilterField value={month} onChange={setMonth} hint="Kosong = semua bulan." />
      </div>
      <OvertimeRecapList query={recap} />
    </PageTemplate>
  );
}
