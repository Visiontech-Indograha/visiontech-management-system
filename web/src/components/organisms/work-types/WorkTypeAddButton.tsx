import { Button } from "@/components/atoms/Button";

/** Tombol "Tambah jenis" (kepala halaman dan keadaan kosong). */
export function WorkTypeAddButton({ onAdd }: { onAdd: () => void }) {
  return <Button onClick={onAdd}>Tambah jenis</Button>;
}
