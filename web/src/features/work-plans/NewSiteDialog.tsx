import { useQuery } from "@tanstack/react-query";
import type L from "leaflet";
import { useEffect, useState } from "react";
import { MapContainer, Marker } from "react-leaflet";
import { Button } from "@/components/ui/button";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { ClickToPlace, MapController, Tiles, type LatLng } from "./PlanLocation";

const INDONESIA: LatLng = [-2.5, 118];

type GeoResult = components["schemas"]["GeoResult"];

export type NewSite = { name: string; description: string; lat: number; lng: number };

const fmt = (v: number) => v.toFixed(6);

/**
 * Modal "Lokasi baru" (flowchart SK2-A): peta Leaflet terpusat di posisi PM, bilah cari seluruh Indonesia,
 * Nama lokasi lengkap, Deskripsi, Latitude/Longitude. Koordinat mengikuti aksi TERAKHIR:
 * isian manual → tertimpa hasil cari → tertimpa geser/klik marker (keputusan pemilik 2026-10-03).
 */
export function NewSiteDialog({
  initial,
  onClose,
  onSave,
}: {
  initial: NewSite | null;
  onClose: () => void;
  onSave: (site: NewSite) => void;
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

  const [point, setPoint] = useState<LatLng | null>(initial ? [initial.lat, initial.lng] : null);
  const [view, setView] = useState<{ center: LatLng; zoom: number }>(
    initial ? { center: [initial.lat, initial.lng], zoom: 16 } : { center: INDONESIA, zoom: 5 },
  );
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [lat, setLat] = useState(initial ? fmt(initial.lat) : "");
  const [lng, setLng] = useState(initial ? fmt(initial.lng) : "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [gpsNote, setGpsNote] = useState<string | null>(null);

  // Titik awal = posisi PM saat membuat SK (bila diizinkan browser).
  useEffect(() => {
    if (initial || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const p: LatLng = [pos.coords.latitude, pos.coords.longitude];
        setPoint((cur) => cur ?? p);
        setLat((cur) => cur || fmt(p[0]));
        setLng((cur) => cur || fmt(p[1]));
        setView({ center: p, zoom: 16 });
      },
      () => setGpsNote("Lokasi Anda tidak dapat dibaca. Cari nama tempat atau klik peta."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, [initial]);

  /** Titik dari cari/geser/klik: menimpa latitude & longitude yang diketik manual. */
  const placeFromMap = (p: LatLng) => {
    setPoint(p);
    setLat(fmt(p[0]));
    setLng(fmt(p[1]));
  };

  const pick = (r: GeoResult) => {
    placeFromMap([r.lat, r.lng]);
    setView({ center: [r.lat, r.lng], zoom: 16 });
    setName(r.name);
  };

  /** Ketik manual: marker ikut pindah bila angkanya sah. */
  const typed = (nextLat: string, nextLng: string) => {
    setLat(nextLat);
    setLng(nextLng);
    const a = Number(nextLat);
    const b = Number(nextLng);
    if (nextLat.trim() && nextLng.trim() && Number.isFinite(a) && Number.isFinite(b) && Math.abs(a) <= 90 && Math.abs(b) <= 180) {
      setPoint([a, b]);
      setView({ center: [a, b], zoom: 16 });
    }
  };

  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    const a = Number(lat);
    const b = Number(lng);
    if (!name.trim()) next.name = "Nama lokasi wajib diisi.";
    if (!lat.trim() || !Number.isFinite(a) || Math.abs(a) > 90) next.lat = "Latitude harus angka -90 sampai 90.";
    if (!lng.trim() || !Number.isFinite(b) || Math.abs(b) > 180) next.lng = "Longitude harus angka -180 sampai 180.";
    setErrors(next);
    if (Object.keys(next).length) return;
    onSave({ name: name.trim(), description: description.trim(), lat: a, lng: b });
  };

  return (
    <Dialog
      open
      title="Lokasi baru"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="new-site-form">
            Simpan lokasi
          </Button>
        </>
      }
    >
      <form id="new-site-form" onSubmit={submit} noValidate>
        <TextField
          label="Cari nama lokasi"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          hint="Seluruh Indonesia, minimal 3 huruf."
          autoComplete="off"
        />
        {q.length >= 3 && (
          <div className="mb-3 text-sm">
            {search.isFetching && <p className="text-mist">Mencari...</p>}
            {search.isError && <p className="text-danger">{errorMessage(search.error)}</p>}
            {search.isSuccess && search.data.length === 0 && <p className="text-mist">Tidak ada hasil.</p>}
            {search.data && search.data.length > 0 && (
              <ul aria-label="Hasil pencarian" className="max-h-40 divide-y divide-line overflow-y-auto rounded-control border border-line">
                {search.data.map((r) => (
                  <li key={`${r.lat},${r.lng},${r.name}`}>
                    <button type="button" className="min-h-11 w-full px-3 py-2 text-left hover:bg-muted" onClick={() => pick(r)}>
                      {r.name}
                      <span className="block text-xs text-mist">{r.type}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <p className="mb-1 text-sm text-mist">Geser penanda atau klik peta untuk mengoreksi titik.</p>
        {gpsNote && <p className="mb-1 text-sm text-warning">{gpsNote}</p>}
        <div className="isolate mb-3 h-64 overflow-hidden rounded-control border border-line">
          <MapContainer center={view.center} zoom={view.zoom} className="h-full w-full">
            <Tiles />
            <MapController center={view.center} zoom={view.zoom} />
            <ClickToPlace onPick={placeFromMap} />
            {point && (
              <Marker
                position={point}
                draggable
                eventHandlers={{
                  dragend: (e) => {
                    const ll = (e.target as L.Marker).getLatLng();
                    placeFromMap([ll.lat, ll.lng]);
                  },
                }}
              />
            )}
          </MapContainer>
        </div>
        <TextField label="Nama lokasi lengkap" value={name} onChange={(e) => setName(e.target.value)} error={errors.name} maxLength={200} />
        <TextAreaField
          label="Deskripsi lokasi"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          hint="Opsional, mis. gedung, lantai, patokan."
          maxLength={500}
        />
        <div className="grid gap-x-3 md:grid-cols-2">
          <TextField label="Latitude" inputMode="decimal" value={lat} onChange={(e) => typed(e.target.value, lng)} error={errors.lat} />
          <TextField label="Longitude" inputMode="decimal" value={lng} onChange={(e) => typed(lat, e.target.value)} error={errors.lng} />
        </div>
      </form>
    </Dialog>
  );
}
