import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Check In Mess" (aksi utama di kepala halaman dan keadaan kosong). */
export function MessAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Check In Mess</ActionButton>;
}
