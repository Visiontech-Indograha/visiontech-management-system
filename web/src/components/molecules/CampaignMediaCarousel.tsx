import { useRef, type TouchEvent } from "react";
import { Button } from "../atoms/Button";
import { Image } from "../atoms/Image";
import { Text } from "../atoms/Text";
import { ArrowLeft, ArrowRight } from "../atoms/Icon";
import { cn } from "@/lib/utils";

export interface CarouselSlide {
  src: string;
  alt: string;
}

const SWIPE_MIN_PX = 40;

/**
 * Tampilan carousel foto K3: foto utuh (object-contain, latar netral), panah, titik indikator,
 * dan penghitung "2 dari 5" yang diumumkan ke pembaca layar. Pengaturan waktu ada di hook `useTimedCarousel`.
 */
export function CampaignMediaCarousel({
  slides,
  index,
  onPrev,
  onNext,
  onGoTo,
  className,
}: {
  slides: CarouselSlide[];
  index: number;
  onPrev: () => void;
  onNext: () => void;
  onGoTo: (index: number) => void;
  className?: string;
}) {
  const touchX = useRef<number | null>(null);
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
    if (start === null || end === undefined || count <= 1) return;
    const dx = end - start;
    if (dx <= -SWIPE_MIN_PX) onNext();
    else if (dx >= SWIPE_MIN_PX) onPrev();
  };

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div
        role="region"
        aria-roledescription="carousel"
        aria-label="Foto panduan K3"
        className="relative overflow-hidden rounded-xl border border-line bg-surface-elevated"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        <div className="flex h-[45vh] items-center justify-center p-2 md:h-[50vh]">
          <Image
            key={current.src}
            src={current.src}
            alt={current.alt}
            className="h-full w-full object-contain"
            draggable={false}
          />
        </div>

        {count > 1 && (
          <>
            <Button
              variant="secondary"
              size="icon"
              aria-label="Foto sebelumnya"
              onClick={onPrev}
              className="absolute top-1/2 left-2 -translate-y-1/2 opacity-90"
            >
              <ArrowLeft />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              aria-label="Foto berikutnya"
              onClick={onNext}
              className="absolute top-1/2 right-2 -translate-y-1/2 opacity-90"
            >
              <ArrowRight />
            </Button>
          </>
        )}

        <Text
          as="span"
          aria-live="polite"
          aria-atomic="true"
          className="absolute right-2 bottom-2 rounded-full bg-black/65 px-2.5 py-1 text-xs font-semibold text-white"
        >
          {active + 1} dari {count}
        </Text>
      </div>

      {count > 1 && (
        <div className="flex flex-wrap items-center justify-center gap-1" role="group" aria-label="Pilih foto">
          {slides.map((slide, i) => (
            <Button
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
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
