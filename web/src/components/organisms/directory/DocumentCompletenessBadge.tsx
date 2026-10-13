import { Pill } from "@/components/molecules/Pill";

export function DocumentCompletenessBadge({ status, missing }: { status?: string | null; missing?: number }) {
  if (!status) return null;
  return status === "COMPLETE" ? (
    <Pill tone="success">Lengkap</Pill>
  ) : (
    <Pill tone="warning">{`Kurang ${missing ?? ""} berkas`.replace("  ", " ")}</Pill>
  );
}
