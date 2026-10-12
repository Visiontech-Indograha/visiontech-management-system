import type { ComponentProps } from "react";
import { Text } from "../atoms/Text";

/** Blok teks untuk organism (paragraf, label kecil, judul bagian lewat `as`). Contoh: <TextBlock className="text-sm text-mist">…</TextBlock> */
export function TextBlock(props: ComponentProps<typeof Text>) {
  return <Text {...props} />;
}
