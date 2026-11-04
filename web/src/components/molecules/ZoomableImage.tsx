import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Button } from "../atoms/Button";
import { Image } from "../atoms/Image";
import { Text } from "../atoms/Text";
import { Minus, Plus } from "../atoms/Icon";
import { cn } from "@/lib/utils";
import {
  ZOOM_MAX,
  ZOOM_MIN,
  ZOOM_RESET,
  clampPan,
  doubleTapZoom,
  zoomAround,
  wheelScale,
  type ZoomState,
} from "@/lib/zoomPan";

const DOUBLE_TAP_MS = 300;
const DOUBLE_TAP_PX = 24;

type Point = { x: number; y: number };

/**
 * Foto yang bisa diperbesar: cubit (pinch), ketuk dua kali, roda mouse / ctrl+scroll, seret untuk geser,
 * dan tombol + / − / Pas layar. Gerakan memakai pointer events dan CSS transform. Zoom tidak mengubah timer.
 * Setiap interaksi memanggil `onInteract` (untuk menunda geser otomatis) dan `onZoomChange`.
 */
export function ZoomableImage({
  src,
  alt,
  onInteract,
  onZoomChange,
  backdrop,
  className,
}: {
  src: string;
  alt: string;
  onInteract?: () => void;
  onZoomChange?: (scale: number) => void;
  /** Latar blur dari foto yang sama (untuk ruang kosong di sisi potret). */
  backdrop?: boolean;
  className?: string;
}) {
  const viewRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<ZoomState>(ZOOM_RESET);
  const zoomRef = useRef(zoom);
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);
  const pointers = useRef(new Map<number, Point>());
  const pinch = useRef<{ distance: number; scale: number } | null>(null);
  const drag = useRef<{ start: Point; origin: ZoomState } | null>(null);
  const lastTap = useRef<{ at: number; at2: Point } | null>(null);

  const viewSize = () => {
    const r = viewRef.current?.getBoundingClientRect();
    return { width: r?.width ?? 1, height: r?.height ?? 1 };
  };
  const toLocal = (clientX: number, clientY: number): Point => {
    const r = viewRef.current?.getBoundingClientRect();
    if (!r) return { x: 0, y: 0 };
    return { x: clientX - r.left - r.width / 2, y: clientY - r.top - r.height / 2 };
  };

  const apply = (next: ZoomState) => {
    setZoom(next);
    onZoomChange?.(next.scale);
    onInteract?.();
  };

  // Roda mouse perlu listener non-pasif agar preventDefault bisa menahan scroll halaman.
  // Handler disimpan di ref agar listener tetap satu dan selalu memakai state terbaru.
  const wheelHandler = useRef<(e: WheelEvent) => void>(() => undefined);
  useEffect(() => {
    wheelHandler.current = (e: WheelEvent) => {
      e.preventDefault();
      const current = zoomRef.current;
      const anchor = toLocal(e.clientX, e.clientY);
      apply(zoomAround(current, wheelScale(current.scale, e.deltaY), anchor, viewSize()));
    };
  });
  useEffect(() => {
    const el = viewRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => wheelHandler.current(e);
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    viewRef.current?.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    onInteract?.();
    const now = Date.now();
    const here = { x: e.clientX, y: e.clientY };
    if (pointers.current.size === 1) {
      const prev = lastTap.current;
      if (prev && now - prev.at < DOUBLE_TAP_MS && Math.hypot(here.x - prev.at2.x, here.y - prev.at2.y) < DOUBLE_TAP_PX) {
        apply(doubleTapZoom(zoomRef.current, toLocal(e.clientX, e.clientY), viewSize()));
        lastTap.current = null;
      } else {
        lastTap.current = { at: now, at2: here };
      }
      drag.current = { start: here, origin: zoomRef.current };
      pinch.current = null;
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      pinch.current = { distance: Math.hypot(a.x - b.x, a.y - b.y), scale: zoomRef.current.scale };
      drag.current = null;
    }
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const view = viewSize();
    if (pinch.current && pointers.current.size >= 2) {
      const [a, b] = [...pointers.current.values()];
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      const ratio = distance / Math.max(1, pinch.current.distance);
      const mid = toLocal((a.x + b.x) / 2, (a.y + b.y) / 2);
      apply(zoomAround(zoomRef.current, pinch.current.scale * ratio, mid, view));
    } else if (drag.current && zoomRef.current.scale > ZOOM_MIN) {
      const dx = e.clientX - drag.current.start.x;
      const dy = e.clientY - drag.current.start.y;
      apply(
        clampPan(
          { scale: drag.current.origin.scale, x: drag.current.origin.x + dx, y: drag.current.origin.y + dy },
          view,
        ),
      );
    }
  };

  const onPointerEnd = (e: ReactPointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    if (pointers.current.size === 0) drag.current = null;
  };

  const zoomBy = (factor: number) => {
    apply(zoomAround(zoomRef.current, zoomRef.current.scale * factor, { x: 0, y: 0 }, viewSize()));
  };

  const { scale, x, y } = zoom;
  const zoomed = scale > ZOOM_MIN;

  return (
    <div
      ref={viewRef}
      className={cn("relative flex h-full w-full touch-none items-center justify-center overflow-hidden select-none", className)}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerEnd}
      onPointerCancel={onPointerEnd}
      onPointerLeave={onPointerEnd}
    >
      {backdrop && (
        <Image
          src={src}
          alt=""
          aria-hidden
          draggable={false}
          className="pointer-events-none absolute inset-0 h-full w-full scale-110 object-cover opacity-35"
          style={{ filter: "blur(28px)" }}
        />
      )}
      <Image
        src={src}
        alt={alt}
        draggable={false}
        decoding="async"
        className="relative h-full w-full object-contain"
        style={{
          transform: `translate(${x}px, ${y}px) scale(${scale})`,
          transformOrigin: "center center",
          willChange: "transform",
        }}
      />

      <div className="absolute top-12 left-2 z-[5] flex items-center gap-1 rounded-full bg-black/55 p-1">
        <Button variant="ghost" size="icon-sm" aria-label="Perkecil" disabled={!zoomed} onClick={() => zoomBy(1 / 1.4)} className="text-white hover:bg-white/15">
          <Minus />
        </Button>
        <Text as="span" className="min-w-[3.25rem] text-center text-xs font-semibold text-white" aria-live="polite">
          {Math.round(scale * 100)}%
        </Text>
        <Button variant="ghost" size="icon-sm" aria-label="Perbesar" disabled={scale >= ZOOM_MAX} onClick={() => zoomBy(1.4)} className="text-white hover:bg-white/15">
          <Plus />
        </Button>
        <Button variant="ghost" size="sm" aria-label="Pas layar" disabled={!zoomed} onClick={() => apply(ZOOM_RESET)} className="text-white hover:bg-white/15">
          Pas layar
        </Button>
      </div>
    </div>
  );
}
