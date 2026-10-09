import { Pill } from "@/components/molecules/Pill";

/** Pemetaan status → badge (docs/06-UI-UX §4). */
export function DocumentExpiryBadge({ level, days }: { level: string | null | undefined; days?: number | null }) {
  switch (level) {
    case "EXPIRED":
      return <Pill tone="danger">Kedaluwarsa</Pill>;
    case "CRITICAL":
      return <Pill tone="danger">≤ 7 hari</Pill>;
    case "WARNING":
      return <Pill tone="warning">≤ 30 hari</Pill>;
    case "NOTICE":
      return <Pill tone="info">≤ 60 hari</Pill>;
    case "OK":
      return days != null ? <Pill tone="success">{`${days} hari lagi`}</Pill> : null;
    default:
      return null;
  }
}

