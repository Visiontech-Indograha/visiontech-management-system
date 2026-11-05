import { useState } from "react";
import { OvertimeTemplate } from "@/components/templates/overtime/OvertimeTemplate";
import { useSession } from "@/stores/sessionStore";
import { useMyOvertime, useOvertimePending } from "@/services/overtimeService";

/** "Lembur": karyawan mengajukan dan melihat status; peninjau (izin review:overtime atau PM/OM) melihat antrean. */
export function OvertimePage() {
  const { me } = useSession();
  const canReview =
    (me?.permissions ?? []).includes("review:overtime") || ["PROJECT_MANAGER", "OPERATIONAL_MANAGER"].includes(me?.role ?? "");
  const [applying, setApplying] = useState(false);
  const mine = useMyOvertime();
  const pending = useOvertimePending();
  return (
    <OvertimeTemplate
      mine={mine}
      pending={pending}
      canReview={canReview}
      applying={applying}
      onApply={() => setApplying(true)}
      onCloseApply={() => setApplying(false)}
    />
  );
}
