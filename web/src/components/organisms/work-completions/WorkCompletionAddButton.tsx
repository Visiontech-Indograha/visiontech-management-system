import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol aksi "+ Buat Order Klien Baru". */
export function WorkCompletionAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>+ Buat Order Klien Baru</ActionButton>;
}
