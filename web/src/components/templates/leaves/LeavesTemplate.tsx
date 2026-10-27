import type { UseQueryResult } from "@tanstack/react-query";
import { LeaveApplyButton } from "@/components/organisms/leaves/LeaveApplyButton";
import { LeaveApplyDialog } from "@/components/organisms/leaves/LeaveApplyDialog";
import { LeaveReviewDialog } from "@/components/organisms/leaves/LeaveReviewDialog";
import { LeaveBalanceCard } from "@/components/organisms/leaves/LeaveBalanceCard";
import { LeaveList } from "@/components/organisms/leaves/LeaveList";
import type { LeaveBalance, LeaveRequest } from "@/services/leaveService";
import { PageTemplate } from "../PageTemplate";

export function LeavesTemplate({
  leaves,
  balance,
  statusFilter,
  onStatusFilterChange,
  canReview,
  canFinalReview,
  applying,
  reviewing,
  onApply,
  onReview,
  onCloseApply,
  onCloseReview,
}: {
  leaves: UseQueryResult<LeaveRequest[]>;
  balance: UseQueryResult<LeaveBalance>;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  canReview: boolean;
  canFinalReview: boolean;
  applying: boolean;
  reviewing: LeaveRequest | null;
  onApply: () => void;
  onReview: (leave: LeaveRequest) => void;
  onCloseApply: () => void;
  onCloseReview: () => void;
}) {
  return (
    <PageTemplate
      title="Cuti & Izin Karyawan"
      description="Pengajuan permohonan cuti tahunan, izin sakit, persetujuan atasan, dan pemantauan kuota tahunan."
      action={<LeaveApplyButton onApply={onApply} />}
    >
      <div className="space-y-6">
        <LeaveBalanceCard balanceQuery={balance} />
        <LeaveList
          leaves={leaves}
          statusFilter={statusFilter}
          onStatusFilterChange={onStatusFilterChange}
          canReview={canReview}
          canFinalReview={canFinalReview}
          onApply={onApply}
          onReview={onReview}
        />
      </div>

      {applying && <LeaveApplyDialog onClose={onCloseApply} />}
      {reviewing && (
        <LeaveReviewDialog leave={reviewing} onClose={onCloseReview} />
      )}
    </PageTemplate>
  );
}
