import { useState } from "react";
import { useListControls } from "@/hooks/useListControls";
import { LeavesTemplate } from "@/components/templates/leaves/LeavesTemplate";
import { useLeaves, useLeaveBalance, type LeaveRequest } from "@/services/leaveService";
import { useSession } from "@/stores/sessionStore";

const LEAVE_STATUSES = ["PENDING", "APPROVED_BY_PM", "APPROVED_BY_HR", "REJECTED", "CANCELLED"] as const;

export function LeavesPage() {
  const { me } = useSession();
  const canReview =
    Boolean(me?.permissions.includes("review:attendance")) ||
    Boolean(me?.permissions.includes("create:plan")) ||
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "ADMIN_HR_GA" ||
    me?.role === "HR" ||
    me?.role === "SUPER_ADMIN";

  // Persetujuan kedua (setelah PM) hanya oleh HR/GA atau admin.
  const canFinalReview = me?.role === "ADMIN_HR_GA" || me?.role === "HR" || me?.role === "SUPER_ADMIN";

  const controls = useListControls({ size: 20 });
  const statusFilter = controls.filter("status", LEAVE_STATUSES);
  const [applying, setApplying] = useState(false);
  const [reviewing, setReviewing] = useState<LeaveRequest | null>(null);
  const [cancelling, setCancelling] = useState<LeaveRequest | null>(null);

  const currentYear = new Date().getFullYear();
  const today = new Date().toISOString().slice(0, 10);

  // Pemohon sendiri, HR, atau OM dapat membatalkan cuti yang sudah disetujui selama hari cutinya belum lewat
  const canCancelLeave = (l: LeaveRequest) =>
    (l.status === "APPROVED_BY_PM" || l.status === "APPROVED_BY_HR") &&
    String(l.end_date).slice(0, 10) >= today &&
    (l.employee_id === me?.employee_id ||
      me?.role === "ADMIN_HR_GA" ||
      me?.role === "HR" ||
      me?.role === "OPERATIONAL_MANAGER");

  // Jika bukan reviewer/admin, batasi daftar ke pengajuan diri sendiri; jika reviewer, tampilkan semua
  const leavesQuery = useLeaves({
    employee_id: canReview ? undefined : (me?.employee_id || undefined),
    status: statusFilter || undefined,
    year: currentYear,
    q: controls.search || undefined,
    page: controls.page,
    size: controls.size,
  });

  const balanceQuery = useLeaveBalance(me?.employee_id ?? "", currentYear);

  return (
    <LeavesTemplate
      leaves={leavesQuery}
      balance={balanceQuery}
      statusFilter={statusFilter}
      onStatusFilterChange={(v) => controls.setFilter("status", v)}
      q={controls.input}
      onQChange={controls.setInput}
      page={controls.page}
      onPageChange={controls.setPage}
      filtersActive={controls.active}
      onResetFilters={controls.reset}
      canReview={canReview}
      canFinalReview={canFinalReview}
      canCancel={canCancelLeave}
      applying={applying}
      reviewing={reviewing}
      cancelling={cancelling}
      onApply={() => setApplying(true)}
      onReview={setReviewing}
      onCancel={setCancelling}
      onCloseApply={() => setApplying(false)}
      onCloseReview={() => setReviewing(null)}
      onCloseCancel={() => setCancelling(null)}
    />
  );
}
