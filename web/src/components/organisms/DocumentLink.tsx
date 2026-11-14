import { ExternalLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";

/** Tautan buka dokumen (PDF/foto) lewat URL bertiket /files/{id}/url; terbuka di tab baru. */
export function DocumentLink({ fileId, label }: { fileId: string; label: string }) {
  const { data: url, isError } = useFileUrl(fileId, "full");
  if (isError) return <TextBlock className="text-xs text-danger">{label} belum bisa dibuka.</TextBlock>;
  if (!url) return <TextBlock className="text-xs text-mist">Menyiapkan {label.toLowerCase()}...</TextBlock>;
  return (
    <ExternalLink href={url} target="_blank" rel="noopener noreferrer" className="inline-block min-h-11 text-sm font-medium text-primary underline">
      {label}
    </ExternalLink>
  );
}
