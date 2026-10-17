import type { UseQueryResult } from "@tanstack/react-query";
import { OffboardingAddButton } from "@/components/organisms/offboarding/OffboardingAddButton";
import { OffboardingFormDialog } from "@/components/organisms/offboarding/OffboardingFormDialog";
import { OffboardingList } from "@/components/organisms/offboarding/OffboardingList";
import type { Offboarding } from "@/services/offboardingService";
import { PageTemplate } from "../PageTemplate";

export function OffboardingTemplate({
  offboardings,
  adding,
  onAdd,
  onVerifyClearance,
  onDecision,
  onCloseAdd,
}: {
  offboardings: UseQueryResult<Offboarding[]>;
  adding: boolean;
  onAdd: () => void;
  onVerifyClearance?: (itemId: string, isCleared: boolean) => void;
  onDecision?: (id: string, approved: boolean) => void;
  onCloseAdd: () => void;
}) {
  return (
    <PageTemplate title="Offboarding & Clearance" action={<OffboardingAddButton onAdd={onAdd} />}>
      <OffboardingList
        offboardings={offboardings}
        onAdd={onAdd}
        onVerifyClearance={onVerifyClearance}
        onDecision={onDecision}
      />
      {adding && <OffboardingFormDialog onClose={onCloseAdd} />}
    </PageTemplate>
  );
}
