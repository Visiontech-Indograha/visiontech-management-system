import { useState } from "react";
import { TimelineTemplate } from "@/components/templates/monitoring/TimelineTemplate";
import { useTimeline } from "@/services/monitoringService";

/** "Timeline tim" (GET /timeline, izin view:timeline): rencana kerja berjalan dikelompokkan per pekerjaan. */
export function TimelinePage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const timeline = useTimeline({ from, to });
  return <TimelineTemplate from={from} to={to} onFromChange={setFrom} onToChange={setTo} timeline={timeline} />;
}
