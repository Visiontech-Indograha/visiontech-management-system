import type { UseQueryResult } from "@tanstack/react-query";
import { MonthFilterField } from "@/components/organisms/monitoring/MonthFilterField";
import { OvertimeRecapList } from "@/components/organisms/monitoring/OvertimeRecapList";
import type { OvertimeRecapRow } from "@/services/monitoringService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Rekap lembur": saringan bulan + daftar rekap. */
export function OvertimeRecapTemplate({ month, onMonthChange, recap }: {
  month: string;
  onMonthChange: (month: string) => void;
  recap: UseQueryResult<OvertimeRecapRow[]>;
}) {
  return (
    <PageTemplate title="Rekap lembur">
      <div className="md:max-w-xs">
        <MonthFilterField value={month} onChange={onMonthChange} hint="Kosong = semua bulan." />
      </div>
      <OvertimeRecapList query={recap} />
    </PageTemplate>
  );
}
