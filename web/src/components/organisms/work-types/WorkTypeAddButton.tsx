import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah jenis" (kepala halaman dan keadaan kosong). */
export function WorkTypeAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Tambah jenis</ActionButton>;
}
