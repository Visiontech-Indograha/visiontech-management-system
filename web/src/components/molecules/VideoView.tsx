import { forwardRef, type ComponentProps } from "react";
import { Video } from "../atoms/Video";

/** Tampilan video untuk organism (mis. pratinjau kamera pendaftaran wajah). */
export const VideoView = forwardRef<HTMLVideoElement, ComponentProps<typeof Video>>(function VideoView(props, ref) {
  return <Video ref={ref} {...props} />;
});
