import { ActionButton } from "@/components/molecules/ActionButton";
import { Plus } from "@/components/molecules/Glyphs";

export function LeaveApplyButton({ onApply }: { onApply: () => void }) {
  return (
    <ActionButton onClick={onApply} className="gap-2">
      <Plus size={16} aria-hidden />
      Ajukan cuti / izin
    </ActionButton>
  );
}
