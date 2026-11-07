import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah divisi" di kepala halaman. */
export function DivisionAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Tambah divisi</ActionButton>;
}
