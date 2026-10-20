import { ActionButton } from "@/components/molecules/ActionButton";
import type { AssetKind } from "@/services/assetService";

/** Tombol "Tambah alat" / "Tambah kendaraan" (izin manage:assets). */
export function AssetCreateButton({ onCreate }: { onCreate: (kind: AssetKind) => void }) {
  return (
    <div className="flex gap-2">
      <ActionButton variant="outline" onClick={() => onCreate("TOOL")}>
        Tambah alat
      </ActionButton>
      <ActionButton onClick={() => onCreate("VEHICLE")}>Tambah kendaraan</ActionButton>
    </div>
  );
}
