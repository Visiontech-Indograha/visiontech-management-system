import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Plus } from "@/components/molecules/Glyphs";

export function WorkOrderCreateAction({ onClick }: { onClick: () => void }) {
  return (
    <ActionButton type="button" variant="default" onClick={onClick}>
      <Plus className="h-4 w-4 mr-1.5" />
      <TextBlock as="span">Buat Work Order Baru</TextBlock>
    </ActionButton>
  );
}
