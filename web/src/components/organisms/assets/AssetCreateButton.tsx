import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah aset" (izin manage:assets). */
export function AssetCreateButton({ onCreate }: { onCreate: () => void }) {
  return <ActionButton onClick={onCreate}>Tambah aset</ActionButton>;
}
