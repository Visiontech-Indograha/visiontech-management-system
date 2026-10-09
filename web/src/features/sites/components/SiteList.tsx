import type { UseQueryResult } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Skeleton } from "@/components/atoms/Skeleton";
import type { Site } from "../siteService";
import { SiteAddButton } from "./SiteAddButton";

/** Daftar lokasi kerja dengan keadaan memuat, galat (+ coba lagi), kosong (+ tambah), dan berhasil. */
export function SiteList({ sites, onAdd, onRemove }: {
  sites: UseQueryResult<Site[]>;
  onAdd: () => void;
  onRemove: (site: Site) => void;
}) {
  return (
    <>
      {sites.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}
      {sites.isError && (
        <div role="alert" className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <p className="mb-3 text-danger">Lokasi kerja tidak dapat dimuat.</p>
          <Button variant="outline" onClick={() => sites.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {sites.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <p className="mb-3 text-mist">Belum ada lokasi kerja. Tambahkan lokasi agar absensi bisa memeriksa radius.</p>
          <SiteAddButton onAdd={onAdd} />
        </div>
      )}
      {sites.data && sites.data.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {sites.data.map((s) => (
            <li key={s.id} className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4">
              <MapPin className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-mist">{s.unit_id ? "Lokasi proyek" : "Lokasi kantor"}</p>
                {s.address && <p className="text-sm text-mist">{s.address}</p>}
                <p className="text-sm text-mist">
                  {s.location.lat.toFixed(6)}, {s.location.lng.toFixed(6)} · radius {s.radius_m} m
                </p>
              </div>
              {s.can_manage && (
                <Button variant="ghost" size="sm" onClick={() => onRemove(s)} aria-label={`Hapus ${s.name}`}>
                  Hapus
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
