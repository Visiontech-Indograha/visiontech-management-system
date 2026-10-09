import { useEffect } from "react";
import { useMap } from "react-leaflet";
import type { LatLng } from "@/lib/geo";

/** Peta di dalam dialog: ukuran dihitung ulang setelah animasi, dan dipusatkan ke titik terpilih. */
export function MapViewController({ center, zoom }: { center: LatLng; zoom: number }) {
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
