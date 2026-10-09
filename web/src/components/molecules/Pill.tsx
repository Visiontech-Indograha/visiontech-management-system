import type { ComponentProps } from "react";
import { Badge } from "../atoms/Badge";

/** Label status kecil bertitik warna. Contoh: <Pill tone="success">Aktif</Pill> */
export function Pill(props: ComponentProps<typeof Badge>) {
  return <Badge {...props} />;
}
