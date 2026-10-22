import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah Tim" (aksi utama di kepala halaman dan keadaan kosong). */
export function TeamAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Tambah Tim</ActionButton>;
}
