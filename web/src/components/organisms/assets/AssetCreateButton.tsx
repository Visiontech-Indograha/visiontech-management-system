import { Button } from "@/components/atoms/Button";

/** Tombol "Tambah aset" (izin manage:assets). */
export function AssetCreateButton({ onCreate }: { onCreate: () => void }) {
  return <Button onClick={onCreate}>Tambah aset</Button>;
}
