import { useEffect, useRef, useState } from "react";
import { ControlInput, ControlLabel, ControlTextarea } from "@/components/molecules/FormBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ArrowLeft, ArrowRight, Trash2, AlertTriangle } from "@/components/molecules/Glyphs";
import { CampaignMediaCarousel } from "./CampaignMediaCarousel";
import { MAX_UPLOAD_BYTES } from "@/services/uploadService";
import { CAROUSEL_MAX_PHOTOS } from "@/lib/hseCarousel";
import {
  LOW_RES_MESSAGE,
  lowResolutionWarning,
  mixedOrientationNote,
  readImageSize,
  type PhotoSize,
} from "@/lib/mediaQuality";
import { cn } from "@/lib/utils";

/** Foto yang dipilih admin: berkas asli, URL pratinjau lokal, dan keterangan (maks 300 karakter). */
export interface CampaignPhotoDraft {
  key: string;
  file: File;
  previewUrl: string;
  caption: string;
}

export const CAPTION_MAX_CHARS = 300;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

let draftSeq = 0;

/**
 * Pemilih beberapa foto kampanye K3: unggah, urutkan, hapus, keterangan per foto, peringatan kualitas
 * (hanya peringatan, tidak memblokir), dan pratinjau carousel serta bingkai ponsel 390x844.
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
  const [sizes, setSizes] = useState<Record<string, PhotoSize>>({});
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
        accepted.push({ key: `photo-${draftSeq}`, file, previewUrl: URL.createObjectURL(file), caption: "" });
      }
    }
    setMessage(problems.length ? problems.join(" ") : null);
    if (accepted.length) {
      onChange([...photos, ...accepted]);
      for (const draft of accepted) {
        readImageSize(draft.file)
          .then((size) => setSizes((prev) => ({ ...prev, [draft.key]: size })))
          .catch(() => undefined);
      }
    }
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

  const setCaption = (index: number, caption: string) => {
    onChange(photos.map((p, i) => (i === index ? { ...p, caption: caption.slice(0, CAPTION_MAX_CHARS) } : p)));
  };

  const knownSizes = photos.map((p) => sizes[p.key]).filter((s): s is PhotoSize => Boolean(s));
  // Foto beresolusi rendah dikumpulkan dalam satu peringatan (nomor urut tampil).
  const lowResFotos = photos.flatMap((p, i) => {
    const size = sizes[p.key];
    return size && lowResolutionWarning(size) ? [String(i + 1)] : [];
  });
  const mixedNote = mixedOrientationNote(knownSizes);
  const slides = photos.map((p, i) => ({
    src: p.previewUrl,
    alt: `Pratinjau foto ${i + 1}: ${p.file.name}`,
    caption: p.caption.trim() || undefined,
  }));
  const currentIndex = Math.min(previewIndex, Math.max(0, photos.length - 1));

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

      {/* Peringatan kualitas: kuning, tidak memblokir unggah. */}
      {lowResFotos.length > 0 && (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <TextBlock as="span">
            Foto {lowResFotos.join(", ")}: {LOW_RES_MESSAGE}
          </TextBlock>
        </div>
      )}
      {mixedNote && (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <TextBlock as="span">{mixedNote}</TextBlock>
        </div>
      )}

      {photos.length > 0 && (
        <div role="list" aria-label="Urutan foto" className="space-y-2">
          {photos.map((photo, i) => (
            <div
              key={photo.key}
              role="listitem"
              className={cn(
                "flex gap-3 rounded-xl border bg-surface p-2",
                i === currentIndex ? "border-primary" : "border-line",
              )}
            >
              <ActionButton
                variant="ghost"
                size="default"
                aria-label={`Lihat pratinjau foto ${i + 1}`}
                onClick={() => setPreviewIndex(i)}
                className="h-auto w-[96px] shrink-0 justify-start p-0"
              >
                <ImageView
                  src={photo.previewUrl}
                  alt=""
                  className="block h-[72px] w-[96px] rounded-lg bg-surface-elevated object-cover"
                />
              </ActionButton>
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <TextBlock as="p" className="truncate text-xs font-semibold text-ink">
                    {i + 1}. {photo.file.name}
                  </TextBlock>
                  <div className="flex shrink-0 items-center gap-0.5">
                    <ActionButton variant="ghost" size="icon-xs" aria-label={`Geser foto ${i + 1} ke kiri`} disabled={i === 0} onClick={() => move(i, i - 1)}>
                      <ArrowLeft />
                    </ActionButton>
                    <ActionButton variant="ghost" size="icon-xs" aria-label={`Geser foto ${i + 1} ke kanan`} disabled={i === photos.length - 1} onClick={() => move(i, i + 1)}>
                      <ArrowRight />
                    </ActionButton>
                    <ActionButton variant="ghost" size="icon-xs" aria-label={`Hapus foto ${i + 1}`} onClick={() => remove(i)}>
                      <Trash2 />
                    </ActionButton>
                  </div>
                </div>
                <ControlLabel htmlFor={`caption-${photo.key}`} className="text-[11px] font-semibold text-mist">
                  Keterangan foto {i + 1} (opsional, maks {CAPTION_MAX_CHARS} karakter)
                </ControlLabel>
                <ControlTextarea
                  id={`caption-${photo.key}`}
                  rows={2}
                  maxLength={CAPTION_MAX_CHARS}
                  value={photo.caption}
                  onChange={(e) => setCaption(i, e.target.value)}
                  placeholder="Poin penting yang harus terbaca di HP"
                  className="w-full rounded-lg border border-line bg-background p-2 text-sm outline-none focus:border-primary"
                />
                <TextBlock as="span" className="self-end text-[11px] text-mist">
                  {photo.caption.length}/{CAPTION_MAX_CHARS}
                </TextBlock>
              </div>
            </div>
          ))}
        </div>
      )}

      {photos.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <div className="min-w-0 space-y-2">
            <TextBlock as="span" className="text-xs font-semibold uppercase tracking-wider text-mist">
              Pratinjau carousel ({photos.length} foto, {durationSeconds} detik)
            </TextBlock>
            <div className="h-[40vh] min-h-[220px] overflow-hidden">
              <CampaignMediaCarousel
                fill
                slides={slides}
                index={currentIndex}
                onPrev={() => setPreviewIndex((i) => (i - 1 + photos.length) % photos.length)}
                onNext={() => setPreviewIndex((i) => (i + 1) % photos.length)}
                onGoTo={setPreviewIndex}
              />
            </div>
          </div>
          <div className="space-y-2">
            <TextBlock as="span" className="text-xs font-semibold uppercase tracking-wider text-mist">
              Tampilan ponsel (390x844)
            </TextBlock>
            {/* Bingkai ponsel: skala 0,5 dari 390x844 agar muat di dialog admin. */}
            <div className="mx-auto h-[422px] w-[195px] overflow-hidden rounded-[22px] border-[6px] border-ink bg-background">
              <CampaignMediaCarousel fill slides={slides} index={currentIndex} onPrev={() => setPreviewIndex((i) => (i - 1 + photos.length) % photos.length)} onNext={() => setPreviewIndex((i) => (i + 1) % photos.length)} onGoTo={setPreviewIndex} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
