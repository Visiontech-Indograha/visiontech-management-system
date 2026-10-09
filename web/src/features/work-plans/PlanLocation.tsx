import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import { Circle, MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { Button } from "@/components/ui/button";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/VmsDialog";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import type { WorkPlan } from "./api";

type S = components["schemas"];
type PlanLocation = S["PlanLocationOut"];
type GeoResult = S["GeoResult"];
export type LatLng = [number, number];

// Vite mengubah nama berkas gambar; ikon penanda bawaan Leaflet perlu URL eksplisit.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow });

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const INDONESIA: LatLng = [-2.5, 118];
const CLOSED = ["COMPLETED", "CANCELLED"];
const RUNNING_NOTE =
  "Rencana kerja ini sudah terbit. Mengubah lokasi menerbitkan dokumen versi baru bertanda tangan Anda; versi lama dan absensi sebelumnya tetap tercatat di lokasi lamanya.";

const locationKey = (planId: string) => ["plan-location", planId] as const;

function usePlanLocation(planId: string) {
  return useQuery({
    queryKey: locationKey(planId),
    queryFn: async () => (await api.get<PlanLocation | null>(`/work-plans/${planId}/location`)).data,
  });
}

export function Tiles() {
  return <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />;
}

/** Peta di dalam dialog: ukuran dihitung ulang setelah animasi, dan dipusatkan ke titik terpilih. */
export function MapController({ center, zoom }: { center: LatLng; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 200);
    return () => clearTimeout(t);
  }, [map]);
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center, zoom]);
  return null;
}

export function ClickToPlace({ onPick }: { onPick: (p: LatLng) => void }) {
  useMapEvents({ click: (e) => onPick([e.latlng.lat, e.latlng.lng]) });
  return null;
}

/** Kartu "Lokasi penugasan" di detail SK: peta baca-saja + nama + radius; pengelola dapat mengatur titik. */
export function PlanLocationCard({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const loc = usePlanLocation(plan.id);
  const routerLocation = useLocation();
  const navigate = useNavigate();
  const canEdit = !!me?.permissions.includes("create:plan") && !CLOSED.includes(plan.status);
  // Ditawarkan langsung setelah draft SK dibuat (state navigasi dari form buat SK).
  const offer = !!(routerLocation.state as { setLocation?: boolean } | null)?.setLocation;
  const [open, setOpen] = useState(() => offer && canEdit);
  useEffect(() => {
    if (offer) navigate(routerLocation.pathname, { replace: true, state: null });
  }, [offer, navigate, routerLocation.pathname]);

  const l = loc.data;
  return (
    <section aria-label="Lokasi penugasan" className="mt-6 rounded-panel border border-line bg-surface shadow-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">Lokasi penugasan</h2>
        {canEdit && (
          <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
            Atur titik lokasi
          </Button>
        )}
      </div>
      {loc.isPending && <Skeleton className="h-48 w-full" />}
      {loc.isError && (
        <p className="text-sm text-danger">
          Lokasi tidak dapat dimuat.{" "}
          <Button variant="outline" size="sm" onClick={() => loc.refetch()}>
            Coba lagi
          </Button>
        </p>
      )}
      {loc.isSuccess && !l && <p className="text-sm text-mist">Titik lokasi absensi belum ditetapkan.</p>}
      {l && (
        <>
          <p className="font-medium">{l.name}</p>
          {l.address && <p className="text-sm text-mist">{l.address}</p>}
          <p className="mb-3 text-sm text-mist">
            Radius absensi {l.radius_m ?? "-"} m · {l.lat.toFixed(6)}, {l.lng.toFixed(6)}
          </p>
          {/* isolate: panel Leaflet (z-index 400+) tidak menimpa dialog (z-50). */}
          <div className="isolate h-56 overflow-hidden rounded-control border border-line md:h-72">
            <MapContainer
              key={`${l.lat},${l.lng},${l.radius_m}`}
              center={[l.lat, l.lng]}
              zoom={15}
              className="h-full w-full"
              dragging={false}
              scrollWheelZoom={false}
              doubleClickZoom={false}
              touchZoom={false}
              keyboard={false}
              zoomControl={false}
            >
              <Tiles />
              <Marker position={[l.lat, l.lng]} />
              {l.radius_m && <Circle center={[l.lat, l.lng]} radius={l.radius_m} />}
            </MapContainer>
          </div>
        </>
      )}
      {open && <LocationDialog plan={plan} current={l ?? null} onClose={() => setOpen(false)} />}
    </section>
  );
}

function LocationDialog({ plan, current, onClose }: { plan: WorkPlan; current: PlanLocation | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  // Debounce 1 detik: paling banyak 1 permintaan pencarian per detik (kebijakan Nominatim).
  const q = useDebouncedValue(query.trim(), 1000);
  const search = useQuery({
    queryKey: ["geo-search", q],
    queryFn: async () => (await api.get<GeoResult[]>("/geo/search", { params: { q } })).data,
    enabled: q.length >= 3,
    staleTime: Infinity,
    retry: false,
  });

  const [point, setPoint] = useState<LatLng | null>(current ? [current.lat, current.lng] : null);
  const [view, setView] = useState<{ center: LatLng; zoom: number }>(
    current ? { center: [current.lat, current.lng], zoom: 15 } : { center: INDONESIA, zoom: 5 },
  );
  const [name, setName] = useState(current?.name ?? "");
  const [address, setAddress] = useState(current?.address ?? "");
  const [radius, setRadius] = useState(String(current?.radius_m ?? 100));
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async (body: S["PlanLocationIn"]) => (await api.put<PlanLocation>(`/work-plans/${plan.id}/location`, body)).data,
    onSuccess: (data) => qc.setQueryData(locationKey(plan.id), data),
  });

  const pick = (r: GeoResult) => {
    setPoint([r.lat, r.lng]);
    setView({ center: [r.lat, r.lng], zoom: 14 });
    if (!name.trim()) setName(r.name);
    if (!address.trim()) setAddress(r.name);
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    const next: Record<string, string> = {};
    const r = Number(radius);
    if (!point) next.point = "Pilih titik pada peta.";
    if (!name.trim()) next.name = "Nama lokasi wajib diisi.";
    if (!Number.isInteger(r) || r < 10 || r > 5000) next.radius = "Radius harus bilangan bulat 10–5000 meter.";
    if (plan.status !== "DRAFT" && !reason.trim()) next.reason = "Alasan perubahan lokasi wajib diisi.";
    setErrors(next);
    if (Object.keys(next).length || !point) return;
    try {
      await save.mutateAsync({ name: name.trim(), address: address.trim() || null, lat: point[0], lng: point[1], radius_m: r, reason: reason.trim() || null });
      toast.success("Titik lokasi disimpan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  const radiusNum = Number(radius);
  return (
    <Dialog
      open
      title="Atur titik lokasi"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={save.isPending}>
            Batal
          </Button>
          <Button type="submit" form="location-form" disabled={save.isPending}>
            {save.isPending ? "Menyimpan..." : "Simpan titik"}
          </Button>
        </>
      }
    >
      <form id="location-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {plan.status !== "DRAFT" && (
          <>
            <p className="mb-3 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">{RUNNING_NOTE}</p>
            <TextAreaField label="Alasan perubahan lokasi (wajib)" value={reason} onChange={(e) => setReason(e.target.value)} error={errors.reason} />
          </>
        )}
        <TextField
          label="Cari kota atau tempat"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          hint="Minimal 3 huruf."
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
        <p className="mb-1 text-sm text-mist">Klik peta untuk menaruh titik, atau geser penanda.</p>
        <div className="isolate mb-1 h-64 overflow-hidden rounded-control border border-line">
          <MapContainer center={view.center} zoom={view.zoom} className="h-full w-full">
            <Tiles />
            <MapController center={view.center} zoom={view.zoom} />
            <ClickToPlace onPick={setPoint} />
            {point && (
              <>
                <Marker
                  position={point}
                  draggable
                  eventHandlers={{
                    dragend: (e) => {
                      const ll = (e.target as L.Marker).getLatLng();
                      setPoint([ll.lat, ll.lng]);
                    },
                  }}
                />
                {radiusNum >= 10 && radiusNum <= 5000 && <Circle center={point} radius={radiusNum} />}
              </>
            )}
          </MapContainer>
        </div>
        <p className={`mb-3 text-sm ${errors.point ? "text-danger" : "text-mist"}`}>
          {errors.point ?? (point ? `Titik: ${point[0].toFixed(6)}, ${point[1].toFixed(6)}` : "Belum ada titik.")}
        </p>
        <TextField label="Nama lokasi" value={name} onChange={(e) => setName(e.target.value)} error={errors.name} maxLength={200} />
        <TextField label="Alamat" value={address} onChange={(e) => setAddress(e.target.value)} hint="Opsional." maxLength={500} />
        <TextField
          label="Radius absensi (meter)"
          inputMode="numeric"
          value={radius}
          onChange={(e) => setRadius(e.target.value)}
          error={errors.radius}
          hint="10–5000 meter."
        />
      </form>
    </Dialog>
  );
}
