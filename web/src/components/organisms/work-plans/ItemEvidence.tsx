import { PhotoStrip } from "@/components/organisms/PhotoStrip";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { photoRefs } from "@/lib/photoRefs";
import { usePlanItem } from "@/services/dailyPlanService";

/** Bukti pekerjaan dari ketua tim: foto realisasi (klik = ukuran penuh), catatan, alasan geser. */
export function ItemEvidence({ itemId }: { itemId: string }) {
  const item = usePlanItem(itemId);
  if (item.isPending) return <LoadingBar className="h-4 w-1/3" />;
  if (!item.data) return <TextBlock className="text-sm text-danger">Bukti tidak dapat dimuat.</TextBlock>;
  const photos = photoRefs(item.data.realization_photos_json);
  return (
    <div className="space-y-2 rounded-control border border-line bg-surface p-3">
      <TextBlock className="text-xs font-semibold uppercase text-mist">{`Foto bukti (${photos.length})`}</TextBlock>
      {photos.length === 0 ? (
        <TextBlock className="text-sm text-mist">Belum ada foto dari tim.</TextBlock>
      ) : (
        <PhotoStrip photos={photos} alt="Foto bukti" />
      )}
      <TextBlock className="text-xs font-semibold uppercase text-mist">Catatan tim</TextBlock>
      <TextBlock className="whitespace-pre-line text-sm">{item.data.notes || "-"}</TextBlock>
      {item.data.delay_reason && <TextBlock className="text-sm text-warning">{`Alasan pindah hari: ${item.data.delay_reason}`}</TextBlock>}
    </div>
  );
}
