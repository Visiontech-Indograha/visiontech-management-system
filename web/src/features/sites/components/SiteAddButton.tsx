import { Button } from "@/components/atoms/Button";

/** Tombol "Tambah lokasi" (aksi utama di kepala halaman dan di keadaan kosong). */
export function SiteAddButton({ onAdd }: { onAdd: () => void }) {
  return <Button onClick={onAdd}>Tambah lokasi</Button>;
}
