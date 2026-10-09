import { forwardRef, type VideoHTMLAttributes } from "react";

/** Atom video (`<video>`), mis. pratinjau kamera. */
export const Video = forwardRef<HTMLVideoElement, VideoHTMLAttributes<HTMLVideoElement>>(function Video(props, ref) {
  return <video ref={ref} {...props} />;
});
