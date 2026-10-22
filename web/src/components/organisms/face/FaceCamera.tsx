import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/lib/errors";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VideoView } from "@/components/molecules/VideoView";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

type Phase = "idle" | "starting" | "stills" | "uploading" | "done" | "error";

/**
 * Kamera wajah web (wajah V2): panduan pose, satu jepretan per pose, lalu `onCaptured`. Kecocokan & kualitas wajah
 * diputuskan SERVER. Bingkai dikirim TIDAK dicerminkan (sama dengan HP) walau pratinjau dicerminkan.
 * Galat yang dilempar `onCaptured` ditampilkan dengan tombol coba lagi.
 */
export function FaceCamera({
  poses,
  startLabel,
  doneMessage,
  onCaptured,
}: {
  poses: string[];
  startLabel: string;
  doneMessage: string;
  onCaptured: (photos: Blob[]) => Promise<void>;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cancelled = useRef(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [hint, setHint] = useState("");
  const [error, setError] = useState<string | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    cancelled.current = false;
    return () => {
      cancelled.current = true;
      stopCamera();
    };
  }, [stopCamera]);

  const snapshot = useCallback(async (): Promise<Blob> => {
    const v = videoRef.current!;
    const scale = Math.min(1, 640 / v.videoWidth);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(v.videoWidth * scale);
    canvas.height = Math.round(v.videoHeight * scale);
    canvas.getContext("2d")!.drawImage(v, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Gagal mengambil gambar."))), "image/jpeg", 0.85),
    );
  }, []);

  const fail = (message: string) => {
    stopCamera();
    setError(message);
    setPhase("error");
  };

  const start = async () => {
    setError(null);
    setPhase("starting");
    setHint("Menyiapkan kamera...");
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      fail("Kamera hanya bisa dibuka lewat alamat HTTPS (https://portal.visiontechindo.com) dan peramban yang mendukungnya.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const v = videoRef.current!;
      v.srcObject = stream;
      await v.play();
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      fail(
        name === "NotAllowedError" || name === "SecurityError"
          ? "Akses kamera ditolak. Ketuk ikon gembok di kolom alamat → Izin → Kamera → Izinkan, lalu coba lagi."
          : name === "NotFoundError" || name === "OverconstrainedError"
            ? "Kamera tidak ditemukan pada perangkat ini."
            : "Kamera tidak dapat dibuka (mungkin sedang dipakai aplikasi lain). Tutup aplikasi kamera lain, lalu coba lagi.",
      );
      return;
    }

    try {
      setPhase("stills");
      const photos: Blob[] = [];
      for (const pose of poses) {
        if (cancelled.current) return;
        setHint(pose);
        await sleep(poses.length > 1 ? 1600 : 700); // beri waktu berpose sebelum jepret
        photos.push(await snapshot());
      }
      stopCamera();

      setPhase("uploading");
      setHint("Memproses...");
      await onCaptured(photos);
      setPhase("done");
    } catch (e) {
      fail(errorMessage(e));
    }
  };

  const running = phase === "starting" || phase === "stills" || phase === "uploading";

  return (
    <div className="space-y-3" data-testid="face-capture">
      <div className="relative mx-auto aspect-[4/3] w-full max-w-md overflow-hidden rounded-lg bg-black">
        <VideoView
          ref={videoRef}
          playsInline
          muted
          className="h-full w-full object-cover"
          style={{ transform: "scaleX(-1)" }}
        />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-[82%] w-[52%] rounded-[50%] border-4 border-white/70 shadow-[0_0_0_999px_rgba(0,0,0,0.35)]" />
        </div>
      </div>

      {running && (
        <TextBlock className="text-center text-base font-semibold" data-testid="face-hint" aria-live="polite">
          {hint}
        </TextBlock>
      )}
      {phase === "idle" && (
        <TextBlock className="text-center text-xs text-mist">
          Duduk di tempat terang, wajah tepat di dalam oval, jarak sekitar satu lengan, lalu ikuti arahan pose.
        </TextBlock>
      )}
      {phase === "error" && (
        <TextBlock role="alert" className="text-center text-sm text-danger">
          {error}
        </TextBlock>
      )}
      {phase === "done" && <TextBlock className="text-center text-sm font-medium text-success">{doneMessage}</TextBlock>}

      {!running && phase !== "done" && (
        <div className="flex justify-center">
          <ActionButton onClick={start}>{phase === "error" ? "Coba Lagi" : startLabel}</ActionButton>
        </div>
      )}
    </div>
  );
}
