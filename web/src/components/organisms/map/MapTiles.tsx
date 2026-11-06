import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import "leaflet/dist/leaflet.css";
import { TileLayer } from "react-leaflet";

// Vite mengubah nama berkas gambar; ikon penanda bawaan Leaflet perlu URL eksplisit.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow });

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** Lapisan ubin OpenStreetMap untuk semua peta (lokasi kerja, lokasi rencana). */
export function MapTiles({ onTileError }: { onTileError?: () => void }) {
  return (
    <TileLayer
      url={TILE_URL}
      attribution={ATTRIBUTION}
      eventHandlers={onTileError ? { tileerror: onTileError } : undefined}
    />
  );
}
