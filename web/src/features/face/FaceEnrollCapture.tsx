import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

/** Id HARUS sama dengan yang dikenali face-service (`/face/challenge-check`). */
const CHALLENGES = [
  { id: "kiri", text: "Tengokkan kepala sedikit ke KIRI" },
  { id: "kanan", text: "Tengokkan kepala sedikit ke KANAN" },
  { id: "atas", text: "Dongakkan kepala sedikit ke ATAS" },
  { id: "buka_mulut", text: "BUKA MULUT Anda" },
  { id: "kedip", text: "KEDIPKAN mata Anda" },
] as const;
const CHALLENGE_COUNT = 2;
const TIMEOUT_MS = 45_000;
const POSES = ["Hadap lurus ke kamera", "Tengok sedikit ke kiri", "Tengok sedikit ke kanan", "Tersenyum ke kamera"];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function pick<T>(items: readonly T[], n: number): T[] {
  const pool = [...items];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j]!, pool[i]!];
  }
  return pool.slice(0, n);
}

interface ChallengeResponse {
  status: "sukses" | "menunggu";
  detail: string;
  proof?: string | null;
}

type Phase = "idle" | "starting" | "challenge" | "stills" | "uploading" | "done" | "error";

/**
 * Pendaftaran wajah lewat webcam (bukan pilih berkas): dua gerakan acak yang diperiksa SERVER, lalu beberapa pose.
 * Bingkai dikirim TIDAK dicerminkan (sama dengan HP) walau pratinjau dicerminkan agar terasa seperti cermin.
 */
export function FaceEnrollCapture({ onEnrolled }: { onEnrolled: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cancelled = useRef(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [hint, setHint] = useState("");
  const [step, setStep] = useState(0);
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
    setStep(0);
    setPhase("starting");
    setHint("Menyiapkan kamera...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const v = videoRef.current!;
      v.srcObject = stream;
      await v.play();
    } catch {
      fail("Kamera tidak dapat dibuka. Izinkan akses kamera pada peramban, lalu coba lagi.");
      return;
    }

    const picked = pick(CHALLENGES, CHALLENGE_COUNT);
    const proofs: string[] = [];
    const deadline = Date.now() + TIMEOUT_MS;
    setPhase("challenge");
    try {
      for (const [i, ch] of picked.entries()) {
        setStep(i);
        setHint(ch.text);
        let proof: string | null = null;
        while (!proof) {
          if (cancelled.current) return;
          if (Date.now() > deadline) {
            fail("Waktu habis. Pastikan wajah terlihat jelas di dalam oval, lalu coba lagi.");
            return;
          }
          const form = new FormData();
          form.append("file", await snapshot(), "frame.jpg");
          form.append("challenge", ch.id);
          try {
            const res = (await api.post<ChallengeResponse>("/face/challenge-check", form)).data;
            if (res.status === "sukses" && res.proof) proof = res.proof;
            else setHint(res.detail || ch.text);
          } catch (e) {
            if (e instanceof ApiError && e.status === 429) await sleep(1500);
            else throw e;
          }
          if (!proof) await sleep(350);
        }
        proofs.push(proof);
      }

      setPhase("stills");
      const photos: Blob[] = [];
      for (const pose of POSES) {
        if (cancelled.current) return;
        setHint(pose);
        await sleep(1600); // beri waktu berpose sebelum jepret
        photos.push(await snapshot());
      }
      stopCamera();

      setPhase("uploading");
      setHint("Mengunggah...");
      const form = new FormData();
      photos.forEach((p, i) => form.append("files", p, `pose${i}.jpg`));
      form.append(
        "liveness",
        JSON.stringify({ challenges: picked.map((c) => c.id), passed: true, proofs }),
      );
      await api.post("/face/enroll", form);
      setPhase("done");
      onEnrolled();
    } catch (e) {
      fail(errorMessage(e));
    }
  };

  const running = phase === "starting" || phase === "challenge" || phase === "stills" || phase === "uploading";

  return (
    <div className="space-y-3" data-testid="face-capture">
      <div className="relative mx-auto aspect-[4/3] w-full max-w-md overflow-hidden rounded-lg bg-black">
        <video
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
        <div className="space-y-1 text-center" aria-live="polite">
          {phase === "challenge" && (
            <p className="text-xs text-mist">{`Tantangan ${step + 1} dari ${CHALLENGE_COUNT}`}</p>
          )}
          <p className="text-base font-semibold" data-testid="face-hint">
            {hint}
          </p>
        </div>
      )}
      {phase === "idle" && (
        <p className="text-center text-xs text-mist">
          Duduk di tempat terang, wajah tepat di dalam oval, jarak sekitar satu lengan. Ikuti dua gerakan acak, lalu
          kamera mengambil beberapa pose.
        </p>
      )}
      {phase === "error" && (
        <p role="alert" className="text-center text-sm text-danger">
          {error}
        </p>
      )}
      {phase === "done" && <p className="text-center text-sm font-medium text-success">Wajah berhasil didaftarkan.</p>}

      {!running && phase !== "done" && (
        <div className="flex justify-center">
          <Button onClick={start}>{phase === "error" ? "Coba Lagi" : "Mulai Pendaftaran Wajah"}</Button>
        </div>
      )}
    </div>
  );
}
