import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Buat rencana kerja" (kepala halaman dan keadaan kosong). */
export function PlanCreateButton({ onCreate }: { onCreate: () => void }) {
  return <ActionButton onClick={onCreate}>Buat rencana kerja</ActionButton>;
}
