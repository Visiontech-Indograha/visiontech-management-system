import { useEffect, useRef, useState } from "react";
import { ControlInput, ControlLabel } from "@/components/molecules/FormBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { CampaignMediaCarousel } from "@/components/molecules/CampaignMediaCarousel";
import { ArrowLeft, ArrowRight, Trash2 } from "@/components/molecules/Glyphs";
import { MAX_UPLOAD_BYTES } from "@/services/uploadService";
import { CAROUSEL_MAX_PHOTOS } from "@/lib/hseCarousel";
import { cn } from "@/lib/utils";

/** Foto yang dipilih admin: berkas asli (diunggah saat terbit) dan URL pratinjau lokal. */
export interface CampaignPhotoDraft {
  key: string;
  file: File;
  previewUrl: string;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

let draftSeq = 0;

/**
 * Pemilih beberapa foto kampanye K3: unggah, urutkan, hapus, dan pratinjau carousel.
 * Foto diunggah saat kampanye diterbitkan; di sini hanya disiapkan dan dipratinjau.
 */
export function HseCampaignPhotosField({
  photos,
  onChange,
  durationSeconds,
}: {
  photos: CampaignPhotoDraft[];
  onChange: (next: CampaignPhotoDraft[]) => void;
  durationSeconds: number;
}) {
  const [message, setMessage] = useState<string | null>(null);
  const [previewIndex, setPreviewIndex] = useState(0);
  const photosRef = useRef(photos);
  useEffect(() => {
    photosRef.current = photos;
  }, [photos]);

  // Lepaskan URL pratinjau saat komponen ditutup.
  useEffect(() => {
    return () => photosRef.current.forEach((p) => URL.revokeObjectURL(p.previewUrl));
  }, []);

  const remainingSlots = CAROUSEL_MAX_PHOTOS - photos.length;
  const perPhoto = photos.length > 0 ? durationSeconds / photos.length : 0;

  const addFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const picked = Array.from(files);
    const problems: string[] = [];
    const accepted: CampaignPhotoDraft[] = [];
    for (const file of picked) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        problems.push(`${file.name}: hanya JPG, PNG, atau WebP.`);
      } else if (file.size > MAX_UPLOAD_BYTES) {
        problems.push(`${file.name}: melebihi 10 MB.`);
      } else if (accepted.length + photos.length >= CAROUSEL_MAX_PHOTOS) {
        problems.push(`${file.name}: maksimal ${CAROUSEL_MAX_PHOTOS} foto.`);
      } else {
        draftSeq += 1;
        accepted.push({ key: `photo-${draftSeq}`, file, previewUrl: URL.createObjectURL(file) });
      }
    }
    setMessage(problems.length ? problems.join(" ") : null);
    if (accepted.length) onChange([...photos, ...accepted]);
  };

  const move = (from: number, to: number) => {
    if (to < 0 || to >= photos.length) return;
    const next = [...photos];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
    setPreviewIndex(to);
  };

  const remove = (index: number) => {
    URL.revokeObjectURL(photos[index].previewUrl);
    onChange(photos.filter((_, i) => i !== index));
    setPreviewIndex(0);
  };

  const slides = photos.map((p, i) => ({ src: p.previewUrl, alt: `Pratinjau foto ${i + 1}: ${p.file.name}` }));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist">
          Foto Panduan K3 (1 sampai {CAROUSEL_MAX_PHOTOS}, JPG/PNG/WebP, maks 10 MB per foto)
        </ControlLabel>
        <TextBlock as="span" className="text-xs text-mist">
          {photos.length} dari {CAROUSEL_MAX_PHOTOS} foto
        </TextBlock>
      </div>

      <ControlInput
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        multiple
        disabled={remainingSlots <= 0}
        aria-describedby="hse-photos-help"
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
        className="w-full rounded-xl border border-line bg-surface p-3 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:font-semibold file:text-primary"
      />
      <TextBlock as="p" id="hse-photos-help" className="text-xs text-mist">
        Foto potret dan lanskap ditampilkan utuh. Urutan di bawah = urutan tampil.
        {photos.length > 0 && ` Setiap foto tampil sekitar ${Math.round(perPhoto)} detik.`}
      </TextBlock>

      {message && (
        <TextBlock as="p" role="alert" className="rounded-lg bg-warning-bg px-3 py-2 text-xs font-medium text-warning">
          {message}
        </TextBlock>
      )}

      {photos.length > 0 && (
        <div role="list" className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="Urutan foto">
          {photos.map((photo, i) => (
            <div
              key={photo.key}
              role="listitem"
              className={cn(
                "flex flex-col gap-1.5 rounded-xl border bg-surface p-1.5",
                i === previewIndex ? "border-primary" : "border-line",
              )}
            >
              <ActionButton
                variant="ghost"
                size="default"
                aria-label={`Lihat pratinjau foto ${i + 1}`}
                onClick={() => setPreviewIndex(i)}
                className="block h-20 w-full overflow-hidden rounded-lg bg-surface-elevated p-0"
              >
                <ImageView
                  src={photo.previewUrl}
                  alt=""
                  className="h-full w-full object-contain"
                />
              </ActionButton>
              <div className="flex items-center justify-between gap-1">
                <TextBlock as="p" className="truncate text-xs font-semibold text-ink">
                  {i + 1}. {photo.file.name}
                </TextBlock>
              </div>
              <div className="flex items-center justify-between gap-1">
                <ActionButton
                  variant="ghost"
                  size="icon-xs"
                  aria-label={`Geser foto ${i + 1} ke kiri`}
                  disabled={i === 0}
                  onClick={() => move(i, i - 1)}
                >
                  <ArrowLeft />
                </ActionButton>
                <ActionButton
                  variant="ghost"
                  size="icon-xs"
                  aria-label={`Geser foto ${i + 1} ke kanan`}
                  disabled={i === photos.length - 1}
                  onClick={() => move(i, i + 1)}
                >
                  <ArrowRight />
                </ActionButton>
                <ActionButton
                  variant="ghost"
                  size="icon-xs"
                  aria-label={`Hapus foto ${i + 1}`}
                  onClick={() => remove(i)}
                >
                  <Trash2 />
                </ActionButton>
              </div>
            </div>
          ))}
        </div>
      )}

      {photos.length > 0 && (
        <div className="space-y-2">
          <TextBlock as="span" className="text-xs font-semibold uppercase tracking-wider text-mist">
            Pratinjau carousel ({photos.length} foto, {durationSeconds} detik)
          </TextBlock>
          <CampaignMediaCarousel
            slides={slides}
            index={Math.min(previewIndex, photos.length - 1)}
            onPrev={() => setPreviewIndex((i) => (i - 1 + photos.length) % photos.length)}
            onNext={() => setPreviewIndex((i) => (i + 1) % photos.length)}
            onGoTo={setPreviewIndex}
          />
        </div>
      )}
    </div>
  );
}
