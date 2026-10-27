import { useState } from "react";
import { LeavesTemplate } from "@/components/templates/leaves/LeavesTemplate";
import { useLeaves, useLeaveBalance, type LeaveRequest } from "@/services/leaveService";
import { useSession } from "@/stores/sessionStore";

export function LeavesPage() {
  const { me } = useSession();
  const canReview =
    Boolean(me?.permissions.includes("review:attendance")) ||
    Boolean(me?.permissions.includes("create:plan")) ||
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "HR" ||
    me?.role === "SUPER_ADMIN";

  const [statusFilter, setStatusFilter] = useState("");
  const [applying, setApplying] = useState(false);
  const [reviewing, setReviewing] = useState<LeaveRequest | null>(null);

  // Jika bukan reviewer/admin, batasi daftar ke pengajuan diri sendiri; jika reviewer, tampilkan semua
  const leavesQuery = useLeaves({
    employee_id: canReview ? undefined : (me?.employee_id || undefined),
    status: statusFilter || undefined,
  });

  const balanceQuery = useLeaveBalance(me?.employee_id ?? "", 2026);

  return (
    <LeavesTemplate
      leaves={leavesQuery}
      balance={balanceQuery}
      statusFilter={statusFilter}
      onStatusFilterChange={setStatusFilter}
      canReview={canReview}
      applying={applying}
      reviewing={reviewing}
      onApply={() => setApplying(true)}
      onReview={setReviewing}
      onCloseApply={() => setApplying(false)}
      onCloseReview={() => setReviewing(null)}
    />
  );
}
