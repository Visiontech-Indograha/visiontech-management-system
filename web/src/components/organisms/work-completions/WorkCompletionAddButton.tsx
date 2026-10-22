import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol aksi "+ Pekerjaan klien baru". */
export function WorkCompletionAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>+ Pekerjaan klien baru</ActionButton>;
}
