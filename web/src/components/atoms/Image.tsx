import type { ImgHTMLAttributes } from "react";

/** Atom gambar (`<img>`). `alt` wajib — kosongkan ("") hanya untuk gambar hiasan. */
export function Image({ alt, ...props }: ImgHTMLAttributes<HTMLImageElement> & { alt: string }) {
  return <img alt={alt} {...props} />;
}
