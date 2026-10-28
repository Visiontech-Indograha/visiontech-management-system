import { useState } from "react";
import { ImageView } from "@/components/molecules/ImageView";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useFileUrl } from "@/hooks/useFileUrl";
import type { PhotoRef } from "@/lib/photoRefs";

function Thumb({ fileId, alt }: { fileId: string; alt: string }) {
  const { data: thumb, isError, isPending } = useFileUrl(fileId, "thumb");
  const [open, setOpen] = useState(false);
  const { data: full } = useFileUrl(open ? fileId : undefined, "view");
  return (
    <div className="grid h-24 w-32 place-items-center overflow-hidden rounded-control border border-line bg-hover">
      {thumb ? (
        <PlainAction className="h-full w-full" aria-label={`Perbesar ${alt}`} onClick={() => setOpen(true)}>
          <ImageView src={thumb} alt={alt} className="h-full w-full object-cover" />
        </PlainAction>
      ) : (
        <TextBlock className="px-1 text-center text-2xs text-mist">
          {isError ? "Foto tidak dapat dimuat" : isPending ? "Memuat…" : ""}
        </TextBlock>
      )}
      <VmsDialog open={open} title={alt} onClose={() => setOpen(false)}>
        <ImageView src={full ?? thumb ?? ""} alt={alt} className="max-h-[70vh] w-full object-contain" />
      </VmsDialog>
    </div>
  );
}

/** Deretan thumbnail foto dari server (klik = ukuran penuh); memakai URL bertiket lewat useFileUrl. */
export function PhotoStrip({ photos, alt = "Foto" }: { photos: PhotoRef[]; alt?: string }) {
  if (photos.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {photos.map((p) => (
        <Thumb key={p.file_id} fileId={p.file_id} alt={alt} />
      ))}
    </div>
  );
}
