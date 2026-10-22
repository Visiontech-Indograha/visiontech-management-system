import { useState } from "react";
import { OffboardingTemplate, type OffboardingDialog } from "@/components/templates/offboarding/OffboardingTemplate";
import { useOffboardings, usePkwtExpiring } from "@/services/offboardingService";
import { useSession } from "@/stores/sessionStore";

/** "Offboarding & Clearance" (Milestone 9): HR mengelola; PM/OM divisi ikut menyetujui karyawan divisinya. */
export function OffboardingPage() {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("manage:offboarding");
  const canApprovePm = ["SUPER_ADMIN", "PROJECT_MANAGER", "OPERATIONAL_MANAGER"].includes(me?.role ?? "");
  const offboardings = useOffboardings();
  const expiring = usePkwtExpiring(30);
  const [dialog, setDialog] = useState<OffboardingDialog>(null);

  return (
    <OffboardingTemplate
      offboardings={offboardings}
      expiring={expiring.data ?? []}
      canManage={canManage}
      canApprovePm={canApprovePm}
      dialog={dialog}
      onDialog={setDialog}
    />
  );
}
