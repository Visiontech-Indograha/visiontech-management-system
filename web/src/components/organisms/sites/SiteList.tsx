import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useClientList } from "@/hooks/useClientList";
import type { UseQueryResult } from "@tanstack/react-query";
import type { Site } from "@/services/siteService";
import { SiteAddButton } from "./SiteAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { MapPin } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { RetryNotice } from "@/components/molecules/RetryNotice";

/** Daftar lokasi kerja dengan keadaan memuat, galat (+ coba lagi), kosong (+ tambah), dan berhasil. */
export function SiteList({ sites, onAdd, onRemove }: {
  sites: UseQueryResult<Site[]>;
  onAdd: () => void;
  onRemove: (site: Site) => void;
}) {
  const view = useClientList(sites.data, (s) => [s.name, s.address], { prefix: "lok_" });
  return (
    <>
      {sites.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {sites.isError && (
        <RetryNotice message="Lokasi kerja tidak dapat dimuat." onRetry={() => sites.refetch()} />
      )}
      {sites.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <TextBlock className="mb-3 text-mist">Belum ada lokasi kerja. Tambahkan lokasi agar absensi bisa memeriksa radius.</TextBlock>
          <SiteAddButton onAdd={onAdd} />
        </div>
      )}
      {sites.data && sites.data.length > 0 && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama atau alamat lokasi..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((s) => (
            <ListEntry key={s.id} className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4">
              <MapPin className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <TextBlock className="font-medium">{s.name}</TextBlock>
                <TextBlock className="text-xs text-mist">{s.unit_id ? "Lokasi proyek" : "Lokasi kantor"}</TextBlock>
                {s.address && <TextBlock className="text-sm text-mist">{s.address}</TextBlock>}
                <TextBlock className="text-sm text-mist">
                  {s.location?.lat != null && s.location?.lng != null ? `${s.location.lat.toFixed(6)}, ${s.location.lng.toFixed(6)}` : "Koordinat belum diatur"} · radius {s.radius_m} m
                </TextBlock>
              </div>
              {s.can_manage && (
                <ActionButton variant="ghost" size="sm" onClick={() => onRemove(s)} aria-label={`Hapus ${s.name}`}>
                  Hapus
                </ActionButton>
              )}
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="lokasi" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}
    </>
  );
}
