import { useState } from "react";
import { OvertimeTemplate } from "@/components/templates/overtime/OvertimeTemplate";
import { canApplyOvertime } from "@/lib/aksiPeran";
import { useSession } from "@/stores/sessionStore";
import { useMyOvertime, useOvertimePending } from "@/services/overtimeService";

/** "Lembur": karyawan mengajukan dan melihat status; peninjau (izin review:overtime atau PM/OM) melihat antrean. */
export function OvertimePage() {
  const { me } = useSession();
  const canReview =
    (me?.permissions ?? []).includes("review:overtime") || ["PROJECT_MANAGER", "OPERATIONAL_MANAGER"].includes(me?.role ?? "");
  const [applying, setApplying] = useState(false);
  const mine = useMyOvertime(me?.employee_id);
  const pending = useOvertimePending();
  return (
    <OvertimeTemplate
      mine={mine}
      pending={pending}
      canReview={canReview}
      canApply={canApplyOvertime(me?.role)}
      applying={applying}
      onApply={() => setApplying(true)}
      onCloseApply={() => setApplying(false)}
    />
  );
}
