import { ActionButton } from "@/components/molecules/ActionButton";
import { Plus } from "@/components/molecules/Glyphs";

export function ClientAddButton({ onAdd }: { onAdd: () => void }) {
  return (
    <ActionButton onClick={onAdd} className="gap-2">
      <Plus size={16} aria-hidden />
      Tambah klien
    </ActionButton>
  );
}
