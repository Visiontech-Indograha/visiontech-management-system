import { ImageView } from "@/components/molecules/ImageView";
import { ExternalLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";
import type { PhotoRef } from "@/lib/photoRefs";

function Thumb({ fileId, alt }: { fileId: string; alt: string }) {
  const { data: thumb, isError, isPending } = useFileUrl(fileId, "thumb");
  const { data: full } = useFileUrl(fileId, "view");
  return (
    <div className="grid h-24 w-32 place-items-center overflow-hidden rounded-control border border-line bg-hover">
      {thumb ? (
        <ExternalLink href={full ?? thumb} target="_blank" rel="noopener">
          <ImageView src={thumb} alt={alt} className="h-full w-full object-cover" />
        </ExternalLink>
      ) : (
        <TextBlock className="px-1 text-center text-2xs text-mist">
          {isError ? "Foto tidak dapat dimuat" : isPending ? "Memuat…" : ""}
        </TextBlock>
      )}
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
