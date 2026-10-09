import type { HTMLAttributes } from "react";

type TextTag = "p" | "span" | "strong" | "em" | "small" | "dt" | "dd" | "pre" | "code" | "h1" | "h2" | "h3" | "h4";

/**
 * Atom teks (docs/33 §2.1): satu-satunya tempat teks/elemen tipografi HTML dirender.
 *
 *   <Text className="text-sm text-mist">Keterangan</Text>
 *   <Text as="h2" className="text-base font-semibold">Judul bagian</Text>
 */
export function Text({ as: Tag = "p", ...props }: HTMLAttributes<HTMLElement> & { as?: TextTag }) {
  return <Tag {...props} />;
}
