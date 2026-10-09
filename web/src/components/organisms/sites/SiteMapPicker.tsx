import { useQuery } from "@tanstack/react-query";
import { Circle, MapContainer, Marker } from "react-leaflet";
import type L from "leaflet";
import { useEffect, useRef, useState } from "react";
import { TextField } from "@/components/molecules/Field";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { errorMessage } from "@/lib/errors";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { ClickToPlace, MapController, Tiles, type LatLng } from "@/components/organisms/work-plans/PlanLocationCard";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { PlainAction } from "@/components/molecules/PlainAction";

type GeoResult = components["schemas"]["GeoResult"];

const INDONESIA: LatLng = [-2.5, 118];
const key = (p: LatLng) => `${p[0].toFixed(6)},${p[1].toFixed(6)}`;

/**
 * Pemilih titik lokasi kerja yang dinamis: cari alamat/tempat (seluruh Indonesia), klik peta, geser penanda.
 * Titik berasal dari induk (`point`) sehingga isian lintang/bujur manual ikut menggeser penanda dan peta.
 * `onPick` dipanggil untuk aksi di peta/hasil cari; `label` = nama hasil cari (untuk mengisi alamat).
 */
export function SiteMapPicker({
  point,
  radius,
  onPick,
}: {
  point: LatLng | null;
  radius: number | null;
  onPick: (p: LatLng, label?: string) => void;
}) {
  const [query, setQuery] = useState("");
  const q = useDebouncedValue(query.trim(), 1000); // kebijakan Nominatim: ≤ 1 permintaan/detik
  const search = useQuery({
    queryKey: ["geo-search", q],
    queryFn: async () => (await api.get<GeoResult[]>("/geo/search", { params: { q } })).data,
    enabled: q.length >= 3,
    staleTime: Infinity,
    retry: false,
  });

  const [view, setView] = useState<{ center: LatLng; zoom: number }>(
    point ? { center: point, zoom: 16 } : { center: INDONESIA, zoom: 5 },
  );
  const [gpsNote, setGpsNote] = useState<string | null>(null);
  // Titik terakhir yang berasal dari peta: perubahan dari luar (ketik manual) memusatkan ulang peta, yang dari peta tidak.
  const fromMap = useRef<string | null>(null);

  useEffect(() => {
    if (point && key(point) !== fromMap.current) {
      fromMap.current = key(point);
      setView({ center: point, zoom: 16 });
    }
  }, [point]);

  // Tanpa titik: pusatkan peta ke posisi pengguna (bila diizinkan browser), tanpa menaruh penanda.
  useEffect(() => {
    if (point || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setView({ center: [pos.coords.latitude, pos.coords.longitude], zoom: 15 }),
      () => setGpsNote("Lokasi Anda tidak dapat dibaca. Cari alamat atau klik peta."),
      { timeout: 8000 },
    );
    // hanya sekali saat dibuka
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const place = (p: LatLng, label?: string) => {
    fromMap.current = key(p);
    onPick(p, label);
  };

  return (
    <div className="mb-3">
      <TextField
        label="Cari alamat atau nama tempat"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        hint="Seluruh Indonesia, minimal 3 huruf. Atau klik peta, geser penanda, atau isi lintang/bujur manual di bawah."
        autoComplete="off"
      />
      {q.length >= 3 && (
        <div className="mb-3 text-sm">
          {search.isFetching && <TextBlock className="text-mist">Mencari...</TextBlock>}
          {search.isError && <TextBlock className="text-danger">{errorMessage(search.error)}</TextBlock>}
          {search.isSuccess && search.data.length === 0 && <TextBlock className="text-mist">Tidak ada hasil.</TextBlock>}
          {search.data && search.data.length > 0 && (
            <ListBlock aria-label="Hasil pencarian" className="max-h-40 divide-y divide-line overflow-y-auto rounded-control border border-line">
              {search.data.map((r) => (
                <ListEntry key={`${r.lat},${r.lng},${r.name}`}>
                  <PlainAction
                    type="button"
                    className="min-h-11 w-full px-3 py-2 text-left hover:bg-muted"
                    onClick={() => {
                      place([r.lat, r.lng], r.name);
                      setView({ center: [r.lat, r.lng], zoom: 17 });
                    }}
                  >
                    {r.name}
                    <TextBlock as="span" className="block text-xs text-mist">{r.type}</TextBlock>
                  </PlainAction>
                </ListEntry>
              ))}
            </ListBlock>
          )}
        </div>
      )}
      {gpsNote && <TextBlock className="mb-1 text-sm text-warning">{gpsNote}</TextBlock>}
      <div className="isolate h-64 overflow-hidden rounded-control border border-line" data-testid="site-map">
        <MapContainer center={view.center} zoom={view.zoom} className="h-full w-full">
          <Tiles />
          <MapController center={view.center} zoom={view.zoom} />
          <ClickToPlace onPick={(p) => place(p)} />
          {point && (
            <>
              <Marker
                position={point}
                draggable
                eventHandlers={{
                  dragend: (e) => {
                    const ll = (e.target as L.Marker).getLatLng();
                    place([ll.lat, ll.lng]);
                  },
                }}
              />
              {radius && radius > 0 && <Circle center={point} radius={radius} />}
            </>
          )}
        </MapContainer>
      </div>
    </div>
  );
}
