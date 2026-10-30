import type { UseQueryResult } from "@tanstack/react-query";
import { MonthFilterField } from "@/components/organisms/monitoring/MonthFilterField";
import { OvertimeRecapList } from "@/components/organisms/monitoring/OvertimeRecapList";
import { OvertimeReviewList } from "@/components/organisms/monitoring/OvertimeReviewList";
import type { Overtime } from "@/services/overtimeService";
import type { OvertimeRecapRow } from "@/services/monitoringService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Rekap lembur": antrean tinjau lembur, saringan bulan, dan daftar rekap. */
export function OvertimeRecapTemplate({ month, onMonthChange, recap, pending }: {
  month: string;
  onMonthChange: (month: string) => void;
  recap: UseQueryResult<OvertimeRecapRow[]>;
  pending: UseQueryResult<Overtime[]>;
}) {
  return (
    <PageTemplate title="Rekap lembur">
      <OvertimeReviewList query={pending} />
      <div className="md:max-w-xs">
        <MonthFilterField value={month} onChange={onMonthChange} hint="Kosong = semua bulan." />
      </div>
      <OvertimeRecapList query={recap} />
    </PageTemplate>
  );
}
