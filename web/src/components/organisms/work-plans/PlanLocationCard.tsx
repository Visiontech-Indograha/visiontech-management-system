import { useEffect, useState } from "react";
import { Circle, MapContainer, Marker } from "react-leaflet";
import { MapTiles } from "@/components/organisms/map/MapTiles";
import { useLocation, useNavigate } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import type { WorkPlan } from "@/services/workPlanService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { usePlanLocation } from "@/services/planLocationService";
import { PlanLocationDialog } from "@/components/organisms/work-plans/PlanLocationDialog";

const CLOSED = ["COMPLETED", "CANCELLED"];



/** Kartu "Lokasi penugasan" di detail rencana kerja: peta baca-saja + nama + radius; pengelola dapat mengatur titik. */
export function PlanLocationCard({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const loc = usePlanLocation(plan.id);
  const routerLocation = useLocation();
  const navigate = useNavigate();
  const canEdit = !!me?.permissions.includes("create:plan") && !CLOSED.includes(plan.status);
  // Ditawarkan langsung setelah draft rencana kerja dibuat (state navigasi dari form buat rencana kerja).
  const offer = !!(routerLocation.state as { setLocation?: boolean } | null)?.setLocation;
  const [open, setOpen] = useState(() => offer && canEdit);
  useEffect(() => {
    if (offer) navigate(routerLocation.pathname, { replace: true, state: null });
  }, [offer, navigate, routerLocation.pathname]);

  const l = loc.data;
  return (
    <section aria-label="Lokasi penugasan" className="mt-6 rounded-panel border border-line bg-surface shadow-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <TextBlock as="h2" className="text-base font-semibold">Lokasi penugasan</TextBlock>
        {canEdit && (
          <ActionButton variant="outline" size="sm" onClick={() => setOpen(true)}>
            Atur titik lokasi
          </ActionButton>
        )}
      </div>
      {loc.isPending && <LoadingBar className="h-48 w-full" />}
      {loc.isError && (
        <TextBlock className="text-sm text-danger">
          Lokasi tidak dapat dimuat.{" "}
          <ActionButton variant="outline" size="sm" onClick={() => loc.refetch()}>
            Coba lagi
          </ActionButton>
        </TextBlock>
      )}
      {loc.isSuccess && !l && <TextBlock className="text-sm text-mist">Titik lokasi absensi belum ditetapkan.</TextBlock>}
      {l && (
        <>
          <TextBlock className="font-medium">{l.name}</TextBlock>
          {l.address && <TextBlock className="text-sm text-mist">{l.address}</TextBlock>}
          <TextBlock className="mb-3 text-sm text-mist">
            Radius absensi {l.radius_m ?? "-"} m · {l.lat.toFixed(6)}, {l.lng.toFixed(6)}
          </TextBlock>
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
              <MapTiles />
              <Marker position={[l.lat, l.lng]} />
              {l.radius_m && <Circle center={[l.lat, l.lng]} radius={l.radius_m} />}
            </MapContainer>
          </div>
        </>
      )}
      {open && <PlanLocationDialog plan={plan} current={l ?? null} onClose={() => setOpen(false)} />}
    </section>
  );
}

