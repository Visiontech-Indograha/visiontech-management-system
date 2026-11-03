import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { MapClickToPlace } from "@/components/organisms/map/MapClickToPlace";
import "leaflet/dist/leaflet.css";
import { useFileUrl } from "@/hooks/useFileUrl";
import { errorMessage } from "@/lib/errors";
import type { LatLng } from "@/lib/geo";
import { useMoveSurveyPoint, type Survey } from "@/services/surveyService";

type Point = Survey["points"][number];
const SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const SAT_ATTR = "Imagery &copy; Esri, Maxar, Earthstar Geographics";

// Warna sama dengan legenda laporan: hijau = sudah terpasang, biru = usulan pemasangan baru.
const STATUS_COLOR = { EXISTING: "#16A34A", PROPOSED: "#0284C7" } as const;

const pin = (n: number, status: keyof typeof STATUS_COLOR = "PROPOSED") =>
  L.divIcon({
    className: "",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<div style="width:30px;height:30px;border-radius:50%;background:${STATUS_COLOR[status]};border:3px solid #fff;color:#fff;font:700 14px/24px sans-serif;text-align:center;box-shadow:0 1px 4px #0008;cursor:grab">${n}</div>`,
  });

const coord = (p: Point): LatLng | null =>
  p.site_lat != null && p.site_lng != null ? [Number(p.site_lat), Number(p.site_lng)] : null;

/** Zoom maksimal yang memuat semua titik, dengan auto-resize container saat modal/tab dibuka. */
function FitPoints({ coords }: { coords: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    const trigger = () => {
      map.invalidateSize();
      if (coords.length === 1) map.setView(coords[0], 18);
      else if (coords.length > 1) map.fitBounds(L.latLngBounds(coords), { padding: [80, 80], maxZoom: 18 });
    };

    const t1 = setTimeout(trigger, 100);
    const t2 = setTimeout(trigger, 300);
    const t3 = setTimeout(trigger, 600);

    const container = map.getContainer();
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined" && container) {
      ro = new ResizeObserver(() => {
        map.invalidateSize();
      });
      ro.observe(container);
    }

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      ro?.disconnect();
    };
  }, [map, coords]);
  return null;
}

function Callout({ point, n }: { point: Point; n: number }) {
  const { data: url } = useFileUrl(point.photos[0]?.file_id, "view");
  return (
    <div className="w-48">
      <TextBlock className="text-xs font-semibold">{`${n}. ${point.name}`}</TextBlock>
      {point.site_lat && point.site_lng && (
        <TextBlock className="text-[10px] text-mist">{`${Number(point.site_lat).toFixed(5)}, ${Number(point.site_lng).toFixed(5)}`}</TextBlock>
      )}
      {url && <ImageView src={url} alt={point.name} className="mt-1 h-32 w-full rounded object-cover shadow-sm" />}
    </div>
  );
}

/** Peta layout titik survei (citra satelit): geser penanda untuk menyesuaikan lokasi tepat. Posisi ini dipakai
 * layout otomatis di laporan (penanda + keterangan + satu foto per titik). */
export function SurveyLayoutMap({ survey }: { survey: Survey }) {
  const move = useMoveSurveyPoint(survey.task_id);
  const [placing, setPlacing] = useState<string | null>(null);
  const coords = useMemo(() => survey.points.map(coord).filter((c): c is LatLng => c !== null), [survey.points]);
  const missing = survey.points.filter((p) => !coord(p));
  const editable = survey.can_move;

  const save = (pointId: string, [lat, lng]: LatLng) =>
    move.mutate({ pointId, lat, lng }, {
      onSuccess: () => toast.success("Posisi titik disimpan. Pratinjau laporan memakai posisi baru."),
      onError: (e) => toast.error(errorMessage(e)),
    });

  return (
    <section aria-label="Peta layout" className="space-y-3">
      <TextBlock className="text-sm text-mist">
        {editable
          ? "Geser penanda ke lokasi pemasangan yang tepat (zoom pakai tombol + / −). Layout di laporan dibuat otomatis dari peta ini."
          : "Layout titik pada laporan (hanya lihat)."}
      </TextBlock>
      {missing.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-control border border-warning/40 bg-warning/10 p-2">
          <TextBlock className="text-sm">
            {placing ? "Klik peta untuk menaruh titik." : `${missing.length} titik belum berkoordinat:`}
          </TextBlock>
          {editable && missing.map((p) => (
            <ActionButton key={p.point_id} size="sm" variant={placing === p.point_id ? "default" : "outline"}
              onClick={() => setPlacing(placing === p.point_id ? null : p.point_id)}>
              {p.name}
            </ActionButton>
          ))}
        </div>
      )}
      <div className="h-[65vh] min-h-[400px] overflow-hidden rounded-panel border border-line shadow-card">
        <MapContainer center={coords[0] ?? [0.79, 101.45]} zoom={coords.length ? 18 : 12} maxZoom={19} scrollWheelZoom={false}
          className="h-full w-full">
          <TileLayer url={SAT_URL} attribution={SAT_ATTR} maxZoom={19} maxNativeZoom={18} />
          <FitPoints coords={coords} />
          {placing && <MapClickToPlace onPick={(c) => { save(placing, c); setPlacing(null); }} />}
          {survey.points.map((p, i) => {
            const c = coord(p);
            return c && (
              <Marker key={`${p.point_id}-${c.join()}`} position={c} icon={pin(i + 1, p.point_status ?? "PROPOSED")} draggable={editable}
                eventHandlers={{ dragend: (e) => {
                  const ll = (e.target as L.Marker).getLatLng();
                  save(p.point_id, [ll.lat, ll.lng]);
                } }}>
                <Tooltip permanent direction={i % 2 ? "left" : "right"} offset={[i % 2 ? -18 : 18, 0]} interactive={false}>
                  <Callout point={p} n={i + 1} />
                </Tooltip>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </section>
  );
}
