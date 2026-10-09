import { Badge } from "@/components/atoms/Badge";

/** Pemetaan status → badge (docs/06-UI-UX §4). */
export function ExpiryBadge({ level, days }: { level: string | null | undefined; days?: number | null }) {
  switch (level) {
    case "EXPIRED":
      return <Badge tone="danger">Kedaluwarsa</Badge>;
    case "CRITICAL":
      return <Badge tone="danger">≤ 7 hari</Badge>;
    case "WARNING":
      return <Badge tone="warning">≤ 30 hari</Badge>;
    case "NOTICE":
      return <Badge tone="info">≤ 60 hari</Badge>;
    case "OK":
      return days != null ? <Badge tone="success">{`${days} hari lagi`}</Badge> : null;
    default:
      return null;
  }
}

export function CompletenessBadge({ status, missing }: { status?: string | null; missing?: number }) {
  if (!status) return null;
  return status === "COMPLETE" ? (
    <Badge tone="success">Lengkap</Badge>
  ) : (
    <Badge tone="warning">{`Kurang ${missing ?? ""} berkas`.replace("  ", " ")}</Badge>
  );
}
