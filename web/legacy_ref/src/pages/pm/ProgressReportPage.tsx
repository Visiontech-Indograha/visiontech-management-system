import { useState } from "react";
import {
  useProgressReports,
  useUpdateProgressReport,
  useDeleteProgressReport,
} from "../../hooks/api/useFieldwork";
import { useEmployees } from "../../hooks/api/useLookups";
import { ProgressReportResponse } from "../../types/fieldwork";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { TextArea } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DetailDrawer, DetailField } from "../../components/ui/DetailDrawer";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";

const ProgressReportPage = () => {
  const { data: reports, isLoading, error } = useProgressReports();
  const { data: employees } = useEmployees();

  const [detailReport, setDetailReport] = useState<ProgressReportResponse | null>(null);
  const [editReport, setEditReport] = useState<ProgressReportResponse | null>(null);
  const [notes, setNotes] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ProgressReportResponse | null>(null);

  const updateReport = useUpdateProgressReport(editReport?.id || "");
  const deleteReport = useDeleteProgressReport();

  if (isLoading) {
    return <LoadingState label="Loading laporan progres..." />;
  }

  if (error || !reports) {
    return <ErrorState label="Gagal memuat laporan progres." />;
  }

  const employeeName = (id: string) => employees?.find((e) => e.id === id)?.full_name || id;

  const openEdit = (report: ProgressReportResponse) => {
    setEditReport(report);
    setNotes(report.notes || "");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateReport.mutateAsync({ notes });
    setEditReport(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteReport.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Laporan Progres Lapangan</h1>
        <p className="mt-1 text-sm text-gray-500">Rekapitulasi pelaporan teknisi dari lapangan.</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Tipe Laporan</TableHeader>
              <TableHeader>Teknisi</TableHeader>
              <TableHeader>Waktu Pelaporan</TableHeader>
              <TableHeader>Catatan</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {reports.length === 0 ? (
              <EmptyTableRow colSpan={5} label="Belum ada laporan progres." />
            ) : (
              reports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell>{report.report_type}</TableCell>
                  <TableCell>{employeeName(report.employee_id)}</TableCell>
                  <TableCell>{new Date(report.created_at).toLocaleString()}</TableCell>
                  <TableCell>{report.notes || "-"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => setDetailReport(report)} className="text-indigo-600 hover:underline text-sm">Detail</button>
                      <button onClick={() => openEdit(report)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => setDeleteTarget(report)} className="text-red-600 hover:underline text-sm">Hapus</button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DetailDrawer isOpen={!!detailReport} onClose={() => setDetailReport(null)} title="Detail Laporan Progres">
        {detailReport && (
          <dl>
            <DetailField label="Tipe Laporan" value={detailReport.report_type} />
            <DetailField label="Teknisi" value={employeeName(detailReport.employee_id)} />
            <DetailField label="Waktu" value={new Date(detailReport.created_at).toLocaleString()} />
            <DetailField label="Catatan" value={detailReport.notes} />
            <DetailField
              label="Metadata"
              value={detailReport.extra_metadata ? <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(detailReport.extra_metadata, null, 2)}</pre> : null}
            />
            <DetailField
              label={`Detail Pekerjaan (${detailReport.details.length})`}
              value={detailReport.details.length > 0 ? (
                <ul className="list-disc pl-4">
                  {detailReport.details.map((d) => <li key={d.id}>{d.item_description} — {d.quantity} {d.unit || ""}</li>)}
                </ul>
              ) : null}
            />
            <DetailField
              label={`Bill of Material (${detailReport.bill_of_materials.length})`}
              value={detailReport.bill_of_materials.length > 0 ? (
                <ul className="list-disc pl-4">
                  {detailReport.bill_of_materials.map((b) => <li key={b.id}>{b.material_name} — {b.quantity} {b.unit || ""}</li>)}
                </ul>
              ) : null}
            />
          </dl>
        )}
      </DetailDrawer>

      <Modal isOpen={!!editReport} onClose={() => setEditReport(null)} title="Edit Catatan Laporan">
        <form onSubmit={handleSave} className="space-y-4">
          <TextArea label="Catatan" value={notes} onChange={(e) => setNotes(e.target.value)} rows={5} />
          <ModalFooter onCancel={() => setEditReport(null)} isSubmitting={updateReport.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message="Hapus laporan progres ini? Detail dan BOM terkait akan ikut terhapus."
        isConfirming={deleteReport.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default ProgressReportPage;
