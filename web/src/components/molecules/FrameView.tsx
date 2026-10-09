import { forwardRef, type ComponentProps } from "react";
import { Frame } from "../atoms/Frame";

/** Bingkai pratinjau dokumen untuk organism. */
export const FrameView = forwardRef<HTMLIFrameElement, ComponentProps<typeof Frame>>(function FrameView(props, ref) {
  return <Frame ref={ref} {...props} />;
});
