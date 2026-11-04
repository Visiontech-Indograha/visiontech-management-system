import type { UseQueryResult } from "@tanstack/react-query";
import { LeaveApplyButton } from "@/components/organisms/leaves/LeaveApplyButton";
import { LeaveApplyDialog } from "@/components/organisms/leaves/LeaveApplyDialog";
import { LeaveReviewDialog } from "@/components/organisms/leaves/LeaveReviewDialog";
import { CancelLeaveDialog } from "@/components/organisms/leaves/CancelLeaveDialog";
import { LeaveBalanceCard } from "@/components/organisms/leaves/LeaveBalanceCard";
import { LeaveList } from "@/components/organisms/leaves/LeaveList";
import { LeaveHrQueueCard } from "@/components/organisms/leaves/LeaveHrQueueCard";
import type { Paged } from "@/lib/paged";
import type { LeaveBalance, LeaveRequest } from "@/services/leaveService";
import { PageTemplate } from "../PageTemplate";

export function LeavesTemplate({
  leaves,
  balance,
  statusFilter,
  onStatusFilterChange,
  q,
  onQChange,
  page,
  onPageChange,
  filtersActive,
  onResetFilters,
  canReview,
  canFinalReview,
  canCancel,
  cancelling,
  onCancel,
  onCloseCancel,
  applying,
  reviewing,
  onApply,
  onReview,
  onCloseApply,
  onCloseReview,
  hrQueueCount,
  onShowHrQueue,
}: {
  hrQueueCount: number;
  onShowHrQueue: () => void;
  leaves: UseQueryResult<Paged<LeaveRequest>>;
  balance: UseQueryResult<LeaveBalance>;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  q: string;
  onQChange: (q: string) => void;
  page: number;
  onPageChange: (page: number) => void;
  filtersActive: boolean;
  onResetFilters: () => void;
  canReview: boolean;
  canFinalReview: boolean;
  canCancel: (leave: LeaveRequest) => boolean;
  cancelling: LeaveRequest | null;
  onCancel: (leave: LeaveRequest) => void;
  onCloseCancel: () => void;
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
        {canFinalReview && (
          <LeaveHrQueueCard count={hrQueueCount} active={statusFilter === "APPROVED_BY_PM"} onShow={onShowHrQueue} />
        )}
        <LeaveList
          leaves={leaves}
          statusFilter={statusFilter}
          onStatusFilterChange={onStatusFilterChange}
          q={q}
          onQChange={onQChange}
          page={page}
          onPageChange={onPageChange}
          filtersActive={filtersActive}
          onResetFilters={onResetFilters}
          canReview={canReview}
          canFinalReview={canFinalReview}
          canCancel={canCancel}
          onApply={onApply}
          onReview={onReview}
          onCancel={onCancel}
        />
      </div>

      {applying && <LeaveApplyDialog onClose={onCloseApply} />}
      {reviewing && (
        <LeaveReviewDialog leave={reviewing} onClose={onCloseReview} />
      )}
      {cancelling && <CancelLeaveDialog leave={cancelling} onClose={onCloseCancel} />}
    </PageTemplate>
  );
}
