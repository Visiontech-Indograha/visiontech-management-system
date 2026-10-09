import { Button } from "@/components/atoms/Button";

/** Tombol "Buat rencana kerja" (kepala halaman dan keadaan kosong). */
export function PlanCreateButton({ onCreate }: { onCreate: () => void }) {
  return <Button onClick={onCreate}>Buat rencana kerja</Button>;
}
