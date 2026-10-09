import { forwardRef, type IframeHTMLAttributes } from "react";

/** Atom bingkai dokumen (`<iframe>`), mis. pratinjau PDF. `title` wajib untuk aksesibilitas. */
export const Frame = forwardRef<HTMLIFrameElement, IframeHTMLAttributes<HTMLIFrameElement> & { title: string }>(function Frame(props, ref) {
  return <iframe ref={ref} {...props} />;
});
