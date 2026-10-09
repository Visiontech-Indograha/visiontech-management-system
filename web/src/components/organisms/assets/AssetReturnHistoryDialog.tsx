import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAssetReturns, type Asset, type AssetReturnItem } from "@/services/assetService";

/** Unduh BAST (GET /assets/returns/{id}/pdf, blob). */
async function downloadBast(asset: Asset, item: AssetReturnItem) {
  try {
    const res = await api.get<Blob>(`/assets/returns/${item.id}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
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
        <Button variant="outline" onClick={onClose}>
          Tutup
        </Button>
      }
    >
      {history.isPending && <p className="text-sm text-mist">Memuat…</p>}
      {history.isError && <p className="text-sm text-danger">Riwayat tidak dapat dimuat.</p>}
      {history.data?.length === 0 && <p className="text-sm text-mist">Belum pernah dikembalikan.</p>}
      <ul className="divide-y divide-line text-sm">
        {history.data?.map((r) => (
          <li key={r.id} className="flex flex-col gap-2 py-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-medium">
                Rencana Kerja {r.plan_number} ·{" "}
                {r.verified_at ? (r.is_accepted ? "Diterima" : "Ditolak") : "Menunggu pemeriksaan"}
              </p>
              <p className="text-mist">
                {r.requested_by_name} · {formatDateTime(r.requested_at)} · kondisi {r.condition_on_return ?? "-"}
                {r.verified_by_name && ` · diperiksa ${r.verified_by_name}`}
              </p>
            </div>
            {r.verified_at && (
              <Button size="sm" variant="outline" onClick={() => downloadBast(asset, r)}>
                Unduh BAST
              </Button>
            )}
          </li>
        ))}
      </ul>
    </VmsDialog>
  );
}
