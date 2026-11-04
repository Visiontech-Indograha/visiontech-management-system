import { useRef, useState, type TouchEvent } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ZoomableImage } from "@/components/molecules/ZoomableImage";
import { ArrowLeft, ArrowRight } from "@/components/molecules/Glyphs";
import { cn } from "@/lib/utils";

export interface CarouselSlide {
  src: string;
  alt: string;
  /** Keterangan teks untuk foto ini (opsional, tampil besar di atas foto). */
  caption?: string;
}

const SWIPE_MIN_PX = 40;

/**
 * Tampilan carousel foto K3: foto utuh (object-contain) yang bisa di-zoom, panah, titik indikator,
 * penghitung "2 dari 5" (diumumkan ke pembaca layar), dan keterangan teks per foto.
 * Pengaturan waktu ada di hook `useTimedCarousel`.
 */
export function CampaignMediaCarousel({
  slides,
  index,
  onPrev,
  onNext,
  onGoTo,
  onInteract,
  className,
  compact = false,
  fill = false,
}: {
  slides: CarouselSlide[];
  index: number;
  onPrev: () => void;
  onNext: () => void;
  onGoTo: (index: number) => void;
  /** Dipanggil saat pengguna zoom/geser foto (untuk menunda geser otomatis). */
  onInteract?: () => void;
  className?: string;
  /** Pratinjau admin: tinggi ~40vh dengan ruang untuk panah di kiri-kanan (tidak menimpa gambar). */
  compact?: boolean;
  /** Mengisi seluruh tinggi induk (popup baca): area foto memakai sisa ruang dengan tinggi stabil antar slide. */
  fill?: boolean;
}) {
  const touchX = useRef<number | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const count = slides.length;
  if (count === 0) return null;
  const active = Math.min(index, count - 1);
  const current = slides[active];

  const onTouchStart = (e: TouchEvent<HTMLDivElement>) => {
    touchX.current = e.touches[0]?.clientX ?? null;
  };
  const onTouchEnd = (e: TouchEvent<HTMLDivElement>) => {
    const start = touchX.current;
    touchX.current = null;
    const end = e.changedTouches[0]?.clientX;
    // Saat foto diperbesar, geser jari menggeser gambar (bukan pindah foto).
    if (zoomed || start === null || end === undefined || count <= 1) return;
    const dx = end - start;
    if (dx <= -SWIPE_MIN_PX) onNext();
    else if (dx >= SWIPE_MIN_PX) onPrev();
  };

  return (
    <div className={cn("flex flex-col gap-2", fill && "h-full min-h-0", className)}>
      <div
        role="region"
        aria-roledescription="carousel"
        aria-label="Foto panduan K3"
        className={cn(
          "relative overflow-hidden rounded-xl border border-line bg-surface-elevated",
          fill && "flex min-h-0 flex-1 flex-col",
        )}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        <div
          className={cn(
            "relative flex items-center justify-center overflow-hidden",
            fill ? "min-h-0 flex-1" : compact ? "h-[40vh] px-12" : "h-[45vh] md:h-[50vh]",
          )}
        >
          <ZoomableImage
            key={current.src}
            src={current.src}
            alt={current.alt}
            backdrop={fill}
            onInteract={onInteract}
            onZoomChange={(scale) => setZoomed(scale > 1)}
            className="absolute inset-0"
          />
        </div>

        {count > 1 && (
          <>
            <ActionButton
              variant="secondary"
              size="icon"
              aria-label="Foto sebelumnya"
              onClick={onPrev}
              className="absolute top-1/2 left-2 -translate-y-1/2 opacity-90"
            >
              <ArrowLeft />
            </ActionButton>
            <ActionButton
              variant="secondary"
              size="icon"
              aria-label="Foto berikutnya"
              onClick={onNext}
              className="absolute top-1/2 right-2 -translate-y-1/2 opacity-90"
            >
              <ArrowRight />
            </ActionButton>
          </>
        )}

        {current.caption && (
          <TextBlock
            as="p"
            className="pointer-events-none absolute right-3 bottom-14 left-3 rounded-lg bg-black/75 px-3 py-2 text-base leading-snug font-medium text-white sm:text-lg"
          >
            {current.caption}
          </TextBlock>
        )}

        <TextBlock
          as="span"
          aria-live="polite"
          aria-atomic="true"
          className="pointer-events-none absolute top-2 left-2 rounded-full bg-black/65 px-2.5 py-1 text-xs font-semibold text-white"
        >
          {active + 1} dari {count}
        </TextBlock>
      </div>

      {count > 1 && (
        <div className="flex flex-wrap items-center justify-center gap-1" role="group" aria-label="Pilih foto">
          {slides.map((slide, i) => (
            <ActionButton
              key={`${slide.src}-${i}`}
              variant="ghost"
              size="icon-xs"
              aria-label={`Tampilkan foto ${i + 1} dari ${count}`}
              aria-current={i === active ? "true" : undefined}
              onClick={() => onGoTo(i)}
            >
              <div
                aria-hidden
                className={cn("h-2.5 w-2.5 rounded-full transition-colors", i === active ? "bg-primary" : "bg-line")}
              />
            </ActionButton>
          ))}
        </div>
      )}
    </div>
  );
}
