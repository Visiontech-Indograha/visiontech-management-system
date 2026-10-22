import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Ajukan Offboarding" (aksi utama di kepala halaman dan keadaan kosong). */
export function OffboardingAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Ajukan Offboarding</ActionButton>;
}
