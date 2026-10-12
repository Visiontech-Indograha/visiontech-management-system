import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Circle, MapContainer, Marker } from "react-leaflet";
import { MapClickToPlace } from "@/components/organisms/map/MapClickToPlace";
import { MapTiles } from "@/components/organisms/map/MapTiles";
import { MapViewController } from "@/components/organisms/map/MapViewController";
import { INDONESIA, type LatLng } from "@/lib/geo";
import { toast } from "sonner";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { WorkPlan } from "@/services/workPlanService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { PlainAction } from "@/components/molecules/PlainAction";
import { FormBlock } from "@/components/molecules/FormBlock";
import { planLocationKey, savePlanLocation, type PlanLocation, type PlanLocationIn } from "@/services/planLocationService";
import { searchPlaces, type GeoResult } from "@/services/geoService";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { DialogActions } from "@/components/molecules/DialogActions";

const RUNNING_NOTE =
  "Rencana kerja ini sudah terbit. Mengubah lokasi menerbitkan dokumen versi baru bertanda tangan Anda; versi lama dan absensi sebelumnya tetap tercatat di lokasi lamanya.";

export function PlanLocationDialog({ plan, current, onClose }: { plan: WorkPlan; current: PlanLocation | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  // Debounce 1 detik: paling banyak 1 permintaan pencarian per detik (kebijakan Nominatim).
  const q = useDebouncedValue(query.trim(), 1000);
  const search = useQuery({
    queryKey: ["geo-search", q],
    queryFn: () => searchPlaces(q),
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
    mutationFn: (body: PlanLocationIn) => savePlanLocation(plan.id, body),
    onSuccess: (data) => qc.setQueryData(planLocationKey(plan.id), data),
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
    <VmsDialog
      open
      title="Atur titik lokasi"
      onClose={onClose}
      footer={
        <DialogActions onCancel={onClose} busy={save.isPending} formId="location-form" submitLabel="Simpan titik" busyLabel="Menyimpan..." />
      }
    >
      <FormBlock id="location-form" onSubmit={submit} noValidate>
        <FormErrorText message={formError} />
        {plan.status !== "DRAFT" && (
          <>
            <TextBlock className="mb-3 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">{RUNNING_NOTE}</TextBlock>
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
            {search.isFetching && <TextBlock className="text-mist">Mencari...</TextBlock>}
            {search.isError && <TextBlock className="text-danger">{errorMessage(search.error)}</TextBlock>}
            {search.isSuccess && search.data.length === 0 && <TextBlock className="text-mist">Tidak ada hasil.</TextBlock>}
            {search.data && search.data.length > 0 && (
              <ListBlock aria-label="Hasil pencarian" className="max-h-40 divide-y divide-line overflow-y-auto rounded-control border border-line">
                {search.data.map((r) => (
                  <ListEntry key={`${r.lat},${r.lng},${r.name}`}>
                    <PlainAction type="button" className="min-h-11 w-full px-3 py-2 text-left hover:bg-muted" onClick={() => pick(r)}>
                      {r.name}
                      <TextBlock as="span" className="block text-xs text-mist">{r.type}</TextBlock>
                    </PlainAction>
                  </ListEntry>
                ))}
              </ListBlock>
            )}
          </div>
        )}
        <TextBlock className="mb-1 text-sm text-mist">Klik peta untuk menaruh titik, atau geser penanda.</TextBlock>
        <div className="isolate mb-1 h-64 overflow-hidden rounded-control border border-line">
          <MapContainer center={view.center} zoom={view.zoom} className="h-full w-full">
            <MapTiles />
            <MapViewController center={view.center} zoom={view.zoom} />
            <MapClickToPlace onPick={setPoint} />
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
        <TextBlock className={`mb-3 text-sm ${errors.point ? "text-danger" : "text-mist"}`}>
          {errors.point ?? (point ? `Titik: ${point[0].toFixed(6)}, ${point[1].toFixed(6)}` : "Belum ada titik.")}
        </TextBlock>
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
      </FormBlock>
    </VmsDialog>
  );
}
