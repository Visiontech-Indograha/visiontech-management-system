import type { DetailsHTMLAttributes, HTMLAttributes } from "react";

/** Atom bagian yang bisa dibuka-tutup (`<details>`). */
export function Disclosure(props: DetailsHTMLAttributes<HTMLDetailsElement>) {
  return <details {...props} />;
}

/** Atom judul bagian buka-tutup (`<summary>`). */
export function DisclosureSummary(props: HTMLAttributes<HTMLElement>) {
  return <summary {...props} />;
}
