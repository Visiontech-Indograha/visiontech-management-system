import { useState } from "react";
import { OffboardingTemplate } from "@/components/templates/offboarding/OffboardingTemplate";
import {
  useOffboardings,
  useVerifyClearanceItem,
  useApproveOffboarding,
} from "@/services/offboardingService";

export function OffboardingPage() {
  const offboardings = useOffboardings();
  const verifyClearance = useVerifyClearanceItem();
  const approveOffboarding = useApproveOffboarding();
  const [adding, setAdding] = useState(false);

  const handleVerifyClearance = async (itemId: string, isCleared: boolean) => {
    await verifyClearance.mutateAsync({ itemId, isCleared });
  };

  const handleDecision = async (id: string, approved: boolean) => {
    await approveOffboarding.mutateAsync({ id, approved });
  };

  return (
    <OffboardingTemplate
      offboardings={offboardings}
      adding={adding}
      onAdd={() => setAdding(true)}
      onVerifyClearance={handleVerifyClearance}
      onDecision={handleDecision}
      onCloseAdd={() => setAdding(false)}
    />
  );
}
