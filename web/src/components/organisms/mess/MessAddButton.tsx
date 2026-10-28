import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol aksi utama halaman Mess; label menyesuaikan tab (penempatan karyawan / tambah mess). */
export function MessAddButton({
  onAdd,
  label = "Tempatkan Karyawan",
}: {
  onAdd: () => void;
  label?: string;
}) {
  return <ActionButton onClick={onAdd}>{label}</ActionButton>;
}
