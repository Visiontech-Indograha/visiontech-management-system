import type { ComponentProps } from "react";
import { Disclosure, DisclosureSummary } from "../atoms/Disclosure";

/** Bagian buka-tutup untuk organism: <DisclosureBlock><DisclosureTitle>…</DisclosureTitle>…</DisclosureBlock> */
export function DisclosureBlock(props: ComponentProps<typeof Disclosure>) {
  return <Disclosure {...props} />;
}
export function DisclosureTitle(props: ComponentProps<typeof DisclosureSummary>) {
  return <DisclosureSummary {...props} />;
}
