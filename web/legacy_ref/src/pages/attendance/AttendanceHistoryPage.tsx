import { useState } from "react";
import { useAttendanceHistory, useCorrectAbsence, useDeleteAbsence } from "../../hooks/api/useAttendance";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Select } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DetailDrawer, DetailField } from "../../components/ui/DetailDrawer";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import { AbsenceResponse } from "../../types/attendance";

const AttendanceHistoryPage = () => {
  const { user } = useAuth();
  const { data: history, isLoading, error } = useAttendanceHistory();
  const correctMutation = useCorrectAbsence();
  const deleteMutation = useDeleteAbsence();

  const [detailTarget, setDetailTarget] = useState<AbsenceResponse | null>(null);
  const [editTarget, setEditTarget] = useState<AbsenceResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AbsenceResponse | null>(null);
  const [form, setForm] = useState({ status: "PRESENT", check_out_time: "" });

  const canCorrect = user?.role === UserRole.HR_HES || user?.role === UserRole.ADMIN;

  const openEdit = (abs: AbsenceResponse) => {
    setEditTarget(abs);
    setForm({
      status: abs.status,
      check_out_time: abs.check_out_time ? abs.check_out_time.slice(0, 16) : "",
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;
    await correctMutation.mutateAsync({
      id: editTarget.id,
      data: {
        status: form.status as AbsenceResponse["status"],
        check_out_time: form.check_out_time ? new Date(form.check_out_time).toISOString() : undefined,
      },
    });
    setEditTarget(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label="Loading riwayat absen..." />;
  if (error || !history) return <ErrorState label="Gagal memuat riwayat absen." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Riwayat Absensi</h1>
        <p className="mt-1 text-sm text-gray-500">Catatan check-in dan check-out lapangan.</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Waktu Check-in</TableHeader>
              <TableHeader>Waktu Check-out</TableHeader>
              <TableHeader>Lokasi</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Sync</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {history.length === 0 ? (
              <EmptyTableRow colSpan={6} label="Belum ada riwayat." />
            ) : (
              history.map((abs) => (
                <TableRow key={abs.id}>
                  <TableCell>{new Date(abs.check_in_time).toLocaleString()}</TableCell>
                  <TableCell>{abs.check_out_time ? new Date(abs.check_out_time).toLocaleString() : "-"}</TableCell>
                  <TableCell>
                    {abs.check_in_location ? `${abs.check_in_location.latitude}, ${abs.check_in_location.longitude}` : "-"}
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex rounded-full bg-blue-100 px-2 text-xs font-semibold leading-5 text-blue-800">
                      {abs.status}
                    </span>
                  </TableCell>
                  <TableCell>{abs.sync_status}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => setDetailTarget(abs)} className="text-gray-600 hover:underline text-sm">Detail</button>
                      {canCorrect && (
                        <>
                          <button onClick={() => openEdit(abs)} className="text-indigo-600 hover:underline text-sm">Koreksi</button>
                          <button onClick={() => setDeleteTarget(abs)} className="text-red-600 hover:underline text-sm">Hapus</button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DetailDrawer isOpen={!!detailTarget} onClose={() => setDetailTarget(null)} title="Detail Absensi">
        {detailTarget && (
          <dl>
            <DetailField label="Check-in" value={new Date(detailTarget.check_in_time).toLocaleString()} />
            <DetailField label="Check-out" value={detailTarget.check_out_time ? new Date(detailTarget.check_out_time).toLocaleString() : null} />
            <DetailField
              label="Lokasi Check-in"
              value={detailTarget.check_in_location ? `${detailTarget.check_in_location.latitude}, ${detailTarget.check_in_location.longitude}` : null}
            />
            <DetailField
              label="Lokasi Check-out"
              value={detailTarget.check_out_location ? `${detailTarget.check_out_location.latitude}, ${detailTarget.check_out_location.longitude}` : null}
            />
            <DetailField label="Status" value={detailTarget.status} />
            <DetailField label="Status Sync" value={detailTarget.sync_status} />
            <DetailField
              label="Foto"
              value={detailTarget.photo_url ? <a href={detailTarget.photo_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">Lihat Foto</a> : null}
            />
          </dl>
        )}
      </DetailDrawer>

      <Modal isOpen={!!editTarget} onClose={() => setEditTarget(null)} title="Koreksi Absensi">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Status"
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
          >
            <option value="PRESENT">Present</option>
            <option value="LATE">Late</option>
            <option value="ABSENT">Absent</option>
            <option value="LEAVE">Leave</option>
          </Select>
          <label className="block text-sm font-medium text-gray-700">
            Waktu Check-out
            <input
              type="datetime-local"
              value={form.check_out_time}
              onChange={(e) => setForm({ ...form, check_out_time: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </label>
          <ModalFooter onCancel={() => setEditTarget(null)} isSubmitting={correctMutation.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message="Hapus record absensi ini? Aksi ini tidak bisa dibatalkan."
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default AttendanceHistoryPage;
