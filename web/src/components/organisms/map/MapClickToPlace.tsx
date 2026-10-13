import { useMapEvents } from "react-leaflet";
import type { LatLng } from "@/lib/geo";

/** Klik peta → kirim titik yang diklik ke `onPick`. */
export function MapClickToPlace({ onPick }: { onPick: (p: LatLng) => void }) {
  useMapEvents({ click: (e) => onPick([e.latlng.lat, e.latlng.lng]) });
  return null;
}
