import { useState } from "react";
import { useListControls } from "@/hooks/useListControls";
import { LeavesTemplate } from "@/components/templates/leaves/LeavesTemplate";
import { useLeaves, useLeaveBalance, type LeaveRequest } from "@/services/leaveService";
import { useSession } from "@/stores/sessionStore";

const LEAVE_STATUSES = ["PENDING", "APPROVED_BY_PM", "APPROVED_BY_HR", "REJECTED", "CANCELLED"] as const;

export function LeavesPage() {
  const { me } = useSession();
  // Sama dengan ALLOWED_REVIEW_ROLES di API (leave_service.py): PM, OM, HR/GA, super admin.
  const canReview = ["PROJECT_MANAGER", "OPERATIONAL_MANAGER", "ADMIN_HR_GA", "SUPER_ADMIN"].includes(me?.role ?? "");

  // Persetujuan kedua (setelah PM) oleh HR/GA, OM, atau admin; PM tidak bisa memutus APPROVED_BY_PM (API).
  const canFinalReview = ["ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"].includes(me?.role ?? "");

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

  // Antrean HR = permohonan yang sudah disetujui atasan (APPROVED_BY_PM) dan menunggu HR
  const hrQueueQuery = useLeaves(
    { status: "APPROVED_BY_PM", year: currentYear, page: 1, size: 1 },
    { enabled: canFinalReview },
  );
  const hrQueueCount = hrQueueQuery.data?.total ?? 0;

  return (
    <LeavesTemplate
      hrQueueCount={hrQueueCount}
      onShowHrQueue={() => controls.setFilter("status", "APPROVED_BY_PM")}
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
