import { InlineStyle } from "../atoms/NativeControls";

/** Gaya cetak halaman (mis. lanskap tanpa margin untuk presentasi). */
export function PrintStyle({ css }: { css: string }) {
  return <InlineStyle css={css} />;
}
