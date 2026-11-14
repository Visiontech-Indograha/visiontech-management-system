import { ActionButton } from "@/components/molecules/ActionButton";
import type { AssetKind } from "@/services/assetService";

/** Tombol "Tambah alat" / "Tambah kendaraan" (izin manage:assets). */
export function AssetCreateButton({ onCreate, onBorrowers }: { onCreate: (kind: AssetKind) => void; onBorrowers?: () => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {onBorrowers && <ActionButton variant="outline" onClick={onBorrowers}>Penerima luar</ActionButton>}
      <ActionButton variant="outline" onClick={() => onCreate("TOOL")}>
        Tambah alat
      </ActionButton>
      <ActionButton onClick={() => onCreate("VEHICLE")}>Tambah kendaraan</ActionButton>
    </div>
  );
}
