import { ActionButton } from "@/components/molecules/ActionButton";
import { Plus } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";

export function WorkOrderAddButton({ onAdd }: { onAdd: () => void }) {
  return (
    <ActionButton
      type="button"
      variant="default"
      onClick={onAdd}
      className="flex items-center gap-1.5"
    >
      <Plus className="h-4 w-4" />
      <TextBlock as="span">Buat Work Order Baru</TextBlock>
    </ActionButton>
  );
}
