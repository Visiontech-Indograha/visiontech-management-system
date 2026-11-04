import { useCallback, useEffect, useRef, useState } from "react";
import {
  nextSlideIndex,
  prevSlideIndex,
  readProgressPercent,
  remainingSeconds,
  slideIntervalMs,
} from "@/lib/hseCarousel";

const TICK_MS = 250;
/** Jeda geser otomatis setelah zoom/geser terakhir (ms). */
const HOLD_MS = 5000;

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Carousel berwaktu untuk kampanye K3.
 * - Timer total (durasi baca) berjalan sejak mount dan TIDAK dipercepat oleh navigasi manual.
 * - Foto bergeser otomatis tiap `totalSeconds / count`. Setiap perpindahan foto (otomatis atau manual)
 *   memulai ulang interval, sehingga pindah manual tidak langsung disusul geseran otomatis.
 * - Dengan prefers-reduced-motion, geser otomatis dimatikan; pengguna tetap bisa pindah manual.
 * - Panah kiri/kanan keyboard pindah foto selama `keyboard` aktif.
 */
export function useTimedCarousel({
  count,
  totalSeconds,
  keyboard = true,
}: {
  count: number;
  totalSeconds: number;
  keyboard?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [reduceMotion] = useState(prefersReducedMotion);

  const safeIndex = count > 0 ? Math.min(index, count - 1) : 0;
  const remaining = remainingSeconds(totalSeconds, elapsedMs);
  const done = remaining === 0;

  // Timer total: satu sumber kebenaran berbasis waktu nyata (tahan terhadap tab yang di-throttle).
  useEffect(() => {
    const start = Date.now();
    const id = window.setInterval(() => {
      const elapsed = Date.now() - start;
      setElapsedMs(elapsed);
      if (elapsed >= totalSeconds * 1000) window.clearInterval(id);
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [totalSeconds]);

  // Geser otomatis. Efek ini dijalankan ulang tiap indeks berubah, jadi interval selalu dihitung dari
  // perpindahan terakhir (otomatis maupun manual). Bila pengguna sedang zoom/geser (holdAutoAdvance),
  // geser ditunda sampai HOLD_MS sejak interaksi terakhir; tidak ditunda bila sisa waktu < HOLD_MS.
  const autoAdvance = count > 1 && !reduceMotion;
  const lastInteractRef = useRef(0);
  const mountedAtRef = useRef(0);
  useEffect(() => {
    mountedAtRef.current = Date.now();
  }, []);
  const holdAutoAdvance = useCallback(() => {
    lastInteractRef.current = Date.now();
  }, []);

  useEffect(() => {
    if (!autoAdvance) return;
    let id = 0;
    const schedule = (delay: number) => {
      id = window.setTimeout(() => {
        const now = Date.now();
        const endsAt = mountedAtRef.current + totalSeconds * 1000;
        const holdLeft = lastInteractRef.current + HOLD_MS - now;
        const secondsLeft = endsAt - now;
        if (holdLeft > 0 && secondsLeft > HOLD_MS) {
          schedule(holdLeft);
          return;
        }
        setIndex((i) => nextSlideIndex(Math.min(i, count - 1), count));
      }, delay);
    };
    schedule(slideIntervalMs(totalSeconds, count));
    return () => window.clearTimeout(id);
  }, [safeIndex, autoAdvance, count, totalSeconds]);

  const goNext = useCallback(() => setIndex((i) => nextSlideIndex(Math.min(i, count - 1), count)), [count]);
  const goPrev = useCallback(() => setIndex((i) => prevSlideIndex(Math.min(i, count - 1), count)), [count]);
  const goTo = useCallback((i: number) => setIndex(Math.max(0, Math.min(i, count - 1))), [count]);

  useEffect(() => {
    if (!keyboard || count <= 1) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") goNext();
      else if (e.key === "ArrowLeft") goPrev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [keyboard, count, goNext, goPrev]);

  return {
    index: safeIndex,
    goNext,
    goPrev,
    goTo,
    holdAutoAdvance,
    remaining,
    done,
    progress: readProgressPercent(totalSeconds, elapsedMs),
  };
}
