import { forwardRef, type CanvasHTMLAttributes } from "react";

/** Atom kanvas (`<canvas>`) untuk tanda tangan atau olah grafis lokal. */
export const Canvas = forwardRef<HTMLCanvasElement, CanvasHTMLAttributes<HTMLCanvasElement>>(
  function Canvas(props, ref) {
    return <canvas ref={ref} {...props} />;
  }
);
