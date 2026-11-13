import { ActionButton } from "@/components/molecules/ActionButton";

export function DeviceAddButton({ onAdd }: { onAdd: () => void }) {
  return <ActionButton onClick={onAdd}>Tambah mesin</ActionButton>;
}
