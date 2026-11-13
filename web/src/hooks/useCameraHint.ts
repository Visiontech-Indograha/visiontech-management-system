import { useEffect, useState, type RefObject } from "react";
import { cameraHint, scoreImageData, type FaceBox } from "@/lib/kualitasKamera";

interface FaceDetectorLike {
  detect: (src: CanvasImageSource) => Promise<
    { boundingBox: { width: number; height: number }; landmarks?: { type?: string; locations: { x: number; y: number }[] }[] }[]
  >;
}
type FaceDetectorCtor = new (opts?: { fastMode?: boolean; maxDetectedFaces?: number }) => FaceDetectorLike;

/** FaceDetector hanya ada di sebagian browser; bila tidak ada, pemeriksaan wajah dilewati tanpa galat. */
function makeDetector(): FaceDetectorLike | null {
  const Ctor = (globalThis as { FaceDetector?: FaceDetectorCtor }).FaceDetector;
  if (!Ctor) return null;
  try {
    return new Ctor({ fastMode: true, maxDetectedFaces: 2 });
  } catch (err) {
    // Pemeriksaan wajah opsional: gagal dibuat = dilewati.
    void err;
    return null;
  }
}

/** Ukur kecerahan (dan wajah bila bisa) tiap `everyMs`; hasilnya petunjuk awam atau null. Hanya saran. */
export function useCameraHint(videoRef: RefObject<HTMLVideoElement | null>, active: boolean, everyMs = 1000): string | null {
  const [hint, setHint] = useState<string | null>(null);
  useEffect(() => {
    if (!active) return;
    const detector = makeDetector();
    const canvas = document.createElement("canvas");
    let stopped = false;
    const tick = async () => {
      const v = videoRef.current;
      if (!v || v.videoWidth < 2) return;
      const w = 160;
      const h = Math.max(2, Math.round((v.videoHeight / v.videoWidth) * w));
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;
      ctx.drawImage(v, 0, 0, w, h);
      const { brightness } = scoreImageData(ctx.getImageData(0, 0, w, h).data, w, h);
      let faces: FaceBox[] | undefined;
      if (detector) {
        try {
          const found = await detector.detect(canvas);
          faces = found.map((f) => ({
            width: f.boundingBox.width,
            height: f.boundingBox.height,
            eyes: f.landmarks?.filter((l) => l.type === "eye").flatMap((l) => l.locations.slice(0, 1)),
          }));
        } catch (err) {
          void err; // detektor gagal sesaat: lewati pemeriksaan wajah
          faces = undefined;
        }
      }
      if (!stopped) setHint(cameraHint(brightness, faces, w, h));
    };
    const id = window.setInterval(() => void tick(), everyMs);
    return () => {
      stopped = true;
      window.clearInterval(id);
    };
  }, [videoRef, active, everyMs]);
  return active ? hint : null;
}
