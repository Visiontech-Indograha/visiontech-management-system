import { useState } from "react";
import { AllocationTemplate } from "@/components/templates/alokasi/AllocationTemplate";
import { useWeeklyMatrix } from "@/services/alokasiService";
import { addDays, useDailyFormOptions, wibDate, weekStart } from "@/services/dailyPlanService";

/** "Alokasi mingguan" (PM/OM): matriks tim × hari untuk merencanakan minggu, bukan mengubah jadwal satu per satu. */
export function AllocationPage() {
  const today = wibDate();
  const [start, setStart] = useState(() => weekStart(today));
  const [divisionId, setDivisionId] = useState("");
  const options = useDailyFormOptions(true);
  const matrix = useWeeklyMatrix(start, divisionId);
  return (
    <AllocationTemplate
      start={start}
      today={today}
      matrix={matrix}
      options={options.data}
      divisionId={divisionId}
      onWeek={(delta) => setStart(delta === null ? weekStart(today) : addDays(start, delta))}
      onDivision={setDivisionId}
    />
  );
}
