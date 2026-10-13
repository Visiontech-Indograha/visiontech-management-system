import type { ComponentProps } from "react";
import { Image } from "../atoms/Image";

/** Gambar untuk organism (logo, foto). `alt` wajib. */
export function ImageView(props: ComponentProps<typeof Image>) {
  return <Image {...props} />;
}
