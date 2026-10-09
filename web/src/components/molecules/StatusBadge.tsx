import { Badge } from "@/components/atoms/Badge";
import { statusLabel, statusTone } from "@/lib/labels";

/** Badge status dengan label & warna dari lib/labels. Contoh: <StatusBadge status="IN_PROGRESS" /> */
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{statusLabel(status)}</Badge>;
}
