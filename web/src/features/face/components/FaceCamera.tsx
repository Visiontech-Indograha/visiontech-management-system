import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, ScanFace, Smile } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ComponentType } from "react";
import { Button } from "@/components/atoms/Button";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";

interface Challenge {
  id: string;
  text: string;
  Icon: ComponentType<{ className?: string }>;
}

/** Id HARUS sama dengan yang dikenali face-service (`/face/challenge-check`). Kiri/kanan = sisi tubuh pengguna. */
const CHALLENGES: Challenge[] = [
  { id: "kiri", text: "Tengokkan kepala ke KIRI", Icon: ArrowLeft },
  { id: "kanan", text: "Tengokkan kepala ke KANAN", Icon: ArrowRight },
  { id: "atas", text: "Dongakkan kepala ke ATAS", Icon: ArrowUp },
  { id: "bawah", text: "Tundukkan kepala ke BAWAH", Icon: ArrowDown },
  { id: "buka_mulut", text: "BUKA MULUT Anda", Icon: Smile },
];
/** Langkah penutup: server hanya memberi panduan meluruskan wajah; TIDAK menerbitkan bukti liveness. */
const STRAIGHTEN: Challenge = { id: "depan", text: "Hadap lurus ke kamera", Icon: ScanFace };
const CHALLENGE_COUNT = 2;
const TIMEOUT_MS = 45_000;
const STRAIGHTEN_MS = 12_000;

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

export interface FaceLiveness {
  challenges: string[];
  passed: boolean;
  proofs: string[];
}

type Phase = "idle" | "starting" | "challenge" | "stills" | "uploading" | "done" | "error";

/**
 * Kamera wajah web: dua gerakan acak yang diperiksa SERVER (bukti bertanda tangan), panduan jarak/arah, lalu pose.
 * Bingkai dikirim TIDAK dicerminkan (sama dengan HP) walau pratinjau dicerminkan agar terasa seperti cermin.
 * `onCaptured` menerima gambar mentah + liveness; galat yang dilempar ditampilkan dengan tombol coba lagi.
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
  onCaptured: (photos: Blob[], liveness: FaceLiveness) => Promise<void>;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cancelled = useRef(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [hint, setHint] = useState("");
  const [current, setCurrent] = useState<Challenge | null>(null);
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

  /** Satu putaran periksa-bingkai untuk `ch`; mengembalikan bukti (atau "" untuk langkah meluruskan) / null bila batal. */
  const runStep = async (ch: Challenge, deadline: number): Promise<string | null | undefined> => {
    setCurrent(ch);
    setHint(ch.text);
    for (;;) {
      if (cancelled.current) return null;
      if (Date.now() > deadline) return undefined;
      const form = new FormData();
      form.append("file", await snapshot(), "frame.jpg");
      form.append("challenge", ch.id);
      try {
        const res = (await api.post<ChallengeResponse>("/face/challenge-check", form)).data;
        if (res.status === "sukses") return res.proof ?? "";
        setHint(res.detail || ch.text);
      } catch (e) {
        if (e instanceof ApiError && e.status === 429) await sleep(1500);
        else throw e;
      }
      await sleep(350);
    }
  };

  const start = async () => {
    setError(null);
    setStep(0);
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

    const picked = pick(CHALLENGES, CHALLENGE_COUNT);
    const proofs: string[] = [];
    const deadline = Date.now() + TIMEOUT_MS;
    setPhase("challenge");
    try {
      for (const [i, ch] of picked.entries()) {
        setStep(i);
        const proof = await runStep(ch, deadline);
        if (proof === null) return;
        if (proof === undefined || proof === "") {
          fail("Waktu habis. Pastikan wajah terlihat jelas di dalam oval, lalu coba lagi.");
          return;
        }
        proofs.push(proof);
      }

      // Luruskan wajah dulu; bila tak kunjung lurus dalam batas waktu tetap lanjut (pemeriksaan wajah memutuskan).
      setStep(CHALLENGE_COUNT);
      const straight = await runStep(STRAIGHTEN, Date.now() + STRAIGHTEN_MS);
      if (straight === null) return;

      setPhase("stills");
      setCurrent(null);
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
      await onCaptured(photos, { challenges: picked.map((c) => c.id), passed: true, proofs });
      setPhase("done");
    } catch (e) {
      fail(errorMessage(e));
    }
  };

  const running = phase === "starting" || phase === "challenge" || phase === "stills" || phase === "uploading";
  const Icon = current?.Icon;

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
        {phase === "challenge" && Icon && (
          <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/60 p-3 text-white">
            <Icon className="h-8 w-8" />
          </div>
        )}
      </div>

      {running && (
        <div className="space-y-1 text-center" aria-live="polite">
          {phase === "challenge" && (
            <p className="text-xs text-mist">
              {step < CHALLENGE_COUNT ? `Tantangan ${step + 1} dari ${CHALLENGE_COUNT}` : "Luruskan wajah"}
            </p>
          )}
          <p className="text-base font-semibold" data-testid="face-hint">
            {hint}
          </p>
        </div>
      )}
      {phase === "idle" && (
        <p className="text-center text-xs text-mist">
          Duduk di tempat terang, wajah tepat di dalam oval, jarak sekitar satu lengan. Ikuti dua gerakan acak (kiri,
          kanan, atas, bawah, atau buka mulut), lalu hadap lurus.
        </p>
      )}
      {phase === "error" && (
        <p role="alert" className="text-center text-sm text-danger">
          {error}
        </p>
      )}
      {phase === "done" && <p className="text-center text-sm font-medium text-success">{doneMessage}</p>}

      {!running && phase !== "done" && (
        <div className="flex justify-center">
          <Button onClick={start}>{phase === "error" ? "Coba Lagi" : startLabel}</Button>
        </div>
      )}
    </div>
  );
}
