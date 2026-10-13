import { forwardRef, type ComponentProps } from "react";
import { PlainButton } from "../atoms/PlainButton";

/** Tombol bergaya bebas untuk organism (tab, ubin, tautan-tombol). Tombol aksi biasa: `ActionButton`. */
export const PlainAction = forwardRef<HTMLButtonElement, ComponentProps<typeof PlainButton>>(function PlainAction(props, ref) {
  return <PlainButton ref={ref} {...props} />;
});
