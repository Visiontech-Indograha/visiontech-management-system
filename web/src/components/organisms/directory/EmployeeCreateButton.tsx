import { Button } from "@/components/atoms/Button";

/** Tombol "Tambah karyawan" di kepala halaman Direktori (izin manage:users). */
export function EmployeeCreateButton({ onCreate }: { onCreate: () => void }) {
  return <Button onClick={onCreate}>Tambah karyawan</Button>;
}
