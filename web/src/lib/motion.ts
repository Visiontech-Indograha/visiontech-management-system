/**
 * Cahaya relatif kursor pada kartu (R-12). Performa dulu:
 * - satu listener `pointermove` pasif untuk seluruh dokumen (delegasi), bukan per kartu;
 * - paling banyak satu tulis CSS variable per frame (requestAnimationFrame);
 * - hanya perangkat dengan kursor presisi & tanpa prefers-reduced-motion.
 * Gaya visualnya di styles/index.css (§4 Gerak).
 */
const CARD = ".shadow-card, [data-slot='card']";

export function installPointerGlow(): () => void {
  if (typeof window === "undefined") return () => {};
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!fine.matches || reduced.matches) return () => {};

  let frame = 0;
  let last: { el: HTMLElement; x: number; y: number } | null = null;

  const flush = () => {
    frame = 0;
    if (!last) return;
    const { el, x, y } = last;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${x - rect.left}px`);
    el.style.setProperty("--my", `${y - rect.top}px`);
  };

  const onMove = (event: PointerEvent) => {
    const el = (event.target as Element | null)?.closest<HTMLElement>(CARD);
    if (!el) return;
    last = { el, x: event.clientX, y: event.clientY };
    if (!frame) frame = requestAnimationFrame(flush);
  };

  document.addEventListener("pointermove", onMove, { passive: true });
  return () => {
    document.removeEventListener("pointermove", onMove);
    if (frame) cancelAnimationFrame(frame);
  };
}
