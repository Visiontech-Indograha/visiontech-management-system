import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol "Tambah karyawan" di kepala halaman Direktori (izin manage:users). */
export function EmployeeCreateButton({ onCreate }: { onCreate: () => void }) {
  return <ActionButton onClick={onCreate}>Tambah karyawan</ActionButton>;
}
