import { StatusBadge } from "@/components/molecules/StatusBadge";

/** Lencana status rencana kerja di kepala halaman detail. */
export function PlanStatusBadge({ status }: { status: string }) {
  return <StatusBadge status={status} />;
}
