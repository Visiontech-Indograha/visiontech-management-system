import { useState } from "react";
import { useLeaves, useApproveLeave, useCancelLeave, useLeaveBalance } from "../../hooks/api/useAttendance";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DetailDrawer, DetailField } from "../../components/ui/DetailDrawer";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import { LeaveRequestResponse } from "../../types/attendance";

const LEAVE_TYPE_LABEL: Record<string, string> = {
  ANNUAL: "Cuti Tahunan",
  SICK: "Cuti Sakit",
  MATERNITY: "Cuti Melahirkan",
  UNPAID: "Cuti Tanpa Gaji",
  OFF_DAY: "Ambil Off Day",
  ADD_OFF_DAY: "Tambah Saldo Off Day",
};

const LeaveApprovalPage = () => {
  const { user } = useAuth();
  const { data: leaves, isLoading, error } = useLeaves();
  const { data: balance } = useLeaveBalance(user?.employee_id);
  const approveLeave = useApproveLeave();
  const cancelLeave = useCancelLeave();

  const [detailTarget, setDetailTarget] = useState<LeaveRequestResponse | null>(null);
  const [cancelTarget, setCancelTarget] = useState<LeaveRequestResponse | null>(null);

  if (isLoading) return <LoadingState label="Loading daftar cuti..." />;
  if (error || !leaves) return <ErrorState label="Gagal memuat daftar cuti." />;

  const handleApprove = (id: string, status: string) => {
    approveLeave.mutate({ leaveId: id, status });
  };

  const handleCancel = async () => {
    if (!cancelTarget) return;
    await cancelLeave.mutateAsync(cancelTarget.id);
    setCancelTarget(null);
  };

  const isPMorOM = user?.role === UserRole.PM || user?.role === UserRole.OM || user?.role === UserRole.ADMIN;

  const canCancel = (l: LeaveRequestResponse) => {
    const isOwner = l.employee_id === user?.employee_id;
    if (isPMorOM) return true;
    return isOwner && l.approval_status === "PENDING";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pengajuan Cuti</h1>
        <p className="mt-1 text-sm text-gray-500">Daftar pengajuan cuti dan status approval.</p>
      </div>

      {balance && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase text-gray-500">Sisa Cuti Tahunan</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{balance.annual_remaining}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase text-gray-500">Sisa Saldo Off Day</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{balance.offday_remaining}</p>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Tipe Cuti</TableHeader>
              <TableHeader>Mulai</TableHeader>
              <TableHeader>Selesai</TableHeader>
              <TableHeader>Alasan</TableHeader>
              <TableHeader>Status Approval</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {leaves.length === 0 ? (
              <EmptyTableRow colSpan={6} label="Belum ada pengajuan cuti." />
            ) : (
              leaves.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{LEAVE_TYPE_LABEL[l.leave_type] || l.leave_type}</TableCell>
                  <TableCell>{l.start_date}</TableCell>
                  <TableCell>{l.end_date}</TableCell>
                  <TableCell>{l.reason}</TableCell>
                  <TableCell>
                    <span className="inline-flex rounded-full bg-yellow-100 px-2 text-xs font-semibold leading-5 text-yellow-800">
                      {l.approval_status}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-3">
                      <button onClick={() => setDetailTarget(l)} className="text-gray-600 hover:underline text-sm">Detail</button>
                      {isPMorOM && (l.approval_status === "PENDING" || (l.approval_status === "APPROVED_PM" && user?.role === UserRole.OM)) && (
                        <>
                          <button
                            onClick={() => handleApprove(l.id, user?.role === UserRole.OM ? "APPROVED_OM" : "APPROVED_PM")}
                            disabled={approveLeave.isPending}
                            className="inline-flex items-center rounded bg-green-600 px-2 py-1 text-xs font-semibold text-white hover:bg-green-700"
                          >
                            Setujui
                          </button>
                          <button
                            onClick={() => handleApprove(l.id, "REJECTED")}
                            disabled={approveLeave.isPending}
                            className="inline-flex items-center rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white hover:bg-red-700"
                          >
                            Tolak
                          </button>
                        </>
                      )}
                      {canCancel(l) && (
                        <button onClick={() => setCancelTarget(l)} className="text-red-600 hover:underline text-sm">Batalkan</button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DetailDrawer isOpen={!!detailTarget} onClose={() => setDetailTarget(null)} title="Detail Pengajuan Cuti">
        {detailTarget && (
          <dl>
            <DetailField label="Tipe Cuti" value={LEAVE_TYPE_LABEL[detailTarget.leave_type] || detailTarget.leave_type} />
            <DetailField label="Tanggal Mulai" value={detailTarget.start_date} />
            <DetailField label="Tanggal Selesai" value={detailTarget.end_date} />
            <DetailField label="Alasan" value={detailTarget.reason} />
            <DetailField label="Status" value={detailTarget.approval_status} />
            <DetailField label="Lampiran" value={detailTarget.attachment_url ? <a href={detailTarget.attachment_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">Buka Lampiran</a> : null} />
          </dl>
        )}
      </DetailDrawer>

      <ConfirmDialog
        isOpen={!!cancelTarget}
        title="Konfirmasi Pembatalan"
        message="Batalkan pengajuan cuti ini?"
        confirmLabel="Batalkan"
        isConfirming={cancelLeave.isPending}
        onConfirm={handleCancel}
        onCancel={() => setCancelTarget(null)}
      />
    </div>
  );
}

export default LeaveApprovalPage;
