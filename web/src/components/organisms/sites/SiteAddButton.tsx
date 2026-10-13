import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah lokasi" (aksi utama di kepala halaman dan di keadaan kosong). */
export function SiteAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Tambah lokasi</ActionButton>;
}
