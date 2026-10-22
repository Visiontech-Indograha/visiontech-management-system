import { ImageView } from "@/components/molecules/ImageView";
import { ExternalLink } from "@/components/molecules/Links";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";
import { usePlanItem } from "@/services/dailyPlanService";

type Photo = { file_id: string; requirement_id?: string | null };

function Thumb({ fileId }: { fileId: string }) {
  const { data: thumb } = useFileUrl(fileId, "thumb");
  const { data: full } = useFileUrl(fileId, "view");
  return (
    <div className="h-24 w-32 overflow-hidden rounded-control border border-line bg-hover">
      {thumb && (
        <ExternalLink href={full ?? thumb} target="_blank" rel="noopener">
          <ImageView src={thumb} alt="Foto bukti" className="h-full w-full object-cover" />
        </ExternalLink>
      )}
    </div>
  );
}

/** Bukti pekerjaan dari ketua tim: foto realisasi (klik = ukuran penuh), catatan, alasan geser. */
export function ItemEvidence({ itemId }: { itemId: string }) {
  const item = usePlanItem(itemId);
  if (item.isPending) return <LoadingBar className="h-4 w-1/3" />;
  if (!item.data) return <TextBlock className="text-sm text-danger">Bukti tidak dapat dimuat.</TextBlock>;
  const photos = ((item.data.realization_photos_json ?? []) as Photo[]).filter((p) => p && p.file_id);
  return (
    <div className="space-y-2 rounded-control border border-line bg-surface p-3">
      <TextBlock className="text-xs font-semibold uppercase text-mist">{`Foto bukti (${photos.length})`}</TextBlock>
      {photos.length === 0 ? (
        <TextBlock className="text-sm text-mist">Belum ada foto dari tim.</TextBlock>
      ) : (
        <div className="flex flex-wrap gap-2">
          {photos.map((p) => (
            <Thumb key={p.file_id} fileId={p.file_id} />
          ))}
        </div>
      )}
      <TextBlock className="text-xs font-semibold uppercase text-mist">Catatan tim</TextBlock>
      <TextBlock className="whitespace-pre-line text-sm">{item.data.notes || "-"}</TextBlock>
      {item.data.delay_reason && <TextBlock className="text-sm text-warning">{`Alasan pindah hari: ${item.data.delay_reason}`}</TextBlock>}
    </div>
  );
}
