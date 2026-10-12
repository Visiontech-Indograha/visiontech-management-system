import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAssetReturns, type Asset, type AssetReturnItem, fetchAssetReturnPdf } from "@/services/assetService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Unduh BAST (GET /assets/returns/{id}/pdf, blob). */
async function downloadBast(asset: Asset, item: AssetReturnItem) {
  try {
    const url = URL.createObjectURL(await fetchAssetReturnPdf(item.id));
    const link = document.createElement("a");
    link.href = url;
    link.download = `BAST-${asset.code}-${item.plan_number ?? ""}.pdf`.replace(/\//g, "-");
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast.error(err instanceof ApiError && err.status === 503 ? "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin." : errorMessage(err));
  }
}

/** Riwayat pengembalian + berita acara serah terima (P6-4). */
export function AssetReturnHistoryDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const history = useAssetReturns(asset.id);
  return (
    <VmsDialog
      open
      title={`Riwayat pengembalian ${asset.name}`}
      onClose={onClose}
      footer={
        <ActionButton variant="outline" onClick={onClose}>
          Tutup
        </ActionButton>
      }
    >
      {history.isPending && <TextBlock className="text-sm text-mist">Memuat…</TextBlock>}
      {history.isError && <TextBlock className="text-sm text-danger">Riwayat tidak dapat dimuat.</TextBlock>}
      {history.data?.length === 0 && <TextBlock className="text-sm text-mist">Belum pernah dikembalikan.</TextBlock>}
      <ListBlock className="divide-y divide-line text-sm">
        {history.data?.map((r) => (
          <ListEntry key={r.id} className="flex flex-col gap-2 py-3 md:flex-row md:items-center md:justify-between">
            <div>
              <TextBlock className="font-medium">
                Rencana Kerja {r.plan_number} ·{" "}
                {r.verified_at ? (r.is_accepted ? "Diterima" : "Ditolak") : "Menunggu pemeriksaan"}
              </TextBlock>
              <TextBlock className="text-mist">
                {r.requested_by_name} · {formatDateTime(r.requested_at)} · kondisi {r.condition_on_return ?? "-"}
                {r.verified_by_name && ` · diperiksa ${r.verified_by_name}`}
              </TextBlock>
            </div>
            {r.verified_at && (
              <ActionButton size="sm" variant="outline" onClick={() => downloadBast(asset, r)}>
                Unduh BAST
              </ActionButton>
            )}
          </ListEntry>
        ))}
      </ListBlock>
    </VmsDialog>
  );
}
