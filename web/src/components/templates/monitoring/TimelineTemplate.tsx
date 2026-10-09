import type { UseQueryResult } from "@tanstack/react-query";
import { DateRangeFilter } from "@/components/organisms/monitoring/DateRangeFilter";
import { TimelineGroupList } from "@/components/organisms/monitoring/TimelineGroupList";
import type { TimelineGroup } from "@/services/monitoringService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Timeline tim": rentang tanggal + kelompok rencana kerja. */
export function TimelineTemplate({ from, to, onFromChange, onToChange, timeline }: {
  from: string;
  to: string;
  onFromChange: (date: string) => void;
  onToChange: (date: string) => void;
  timeline: UseQueryResult<TimelineGroup[]>;
}) {
  return (
    <PageTemplate title="Timeline tim">
      <DateRangeFilter from={from} to={to} onFromChange={onFromChange} onToChange={onToChange} />
      <TimelineGroupList query={timeline} />
    </PageTemplate>
  );
}
