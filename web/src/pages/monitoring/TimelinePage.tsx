import { useState } from "react";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { DateRangeFilter } from "@/components/organisms/monitoring/DateRangeFilter";
import { TimelineGroupList } from "@/components/organisms/monitoring/TimelineGroupList";
import { useTimeline } from "@/services/monitoringService";

/** "Timeline tim" (GET /timeline, izin view:timeline): rencana kerja berjalan dikelompokkan per pekerjaan. */
export function TimelinePage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const timeline = useTimeline({ from, to });
  return (
    <PageTemplate title="Timeline tim">
      <DateRangeFilter from={from} to={to} onFromChange={setFrom} onToChange={setTo} />
      <TimelineGroupList query={timeline} />
    </PageTemplate>
  );
}
