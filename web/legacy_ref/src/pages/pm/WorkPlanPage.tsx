import { useState } from "react";
import {
  useWorkPlans,
  useCreateWorkPlan,
  useUpdateWorkPlan,
  useDeleteWorkPlan,
  type WorkPlanCreatePayload,
} from "../../hooks/api/useFieldwork";
import { useEmployees } from "../../hooks/api/useLookups";
import { WorkPlanResponse } from "../../types/fieldwork";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select, TextArea } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DetailDrawer, DetailField } from "../../components/ui/DetailDrawer";
import { SearchBar } from "../../components/ui/SearchBar";
import { Pagination } from "../../components/ui/Pagination";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

const PAGE_SIZE = 20;
const EMPTY_FORM = { title: "", description: "", assignee_id: "", planned_date: "", status: "DRAFT", member_ids: [] as string[] };

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  ACTIVE: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
};

const WorkPlanPage = () => {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput);
  const [statusFilter, setStatusFilter] = useState("");
  const [skip, setSkip] = useState(0);

  const { data: workPlans, isLoading, error } = useWorkPlans({
    q: search || undefined,
    status_filter: statusFilter || undefined,
    skip,
    limit: PAGE_SIZE,
  });
  const { data: employees } = useEmployees();
  const createWorkPlan = useCreateWorkPlan();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<WorkPlanResponse | null>(null);
  const [detailPlan, setDetailPlan] = useState<WorkPlanResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WorkPlanResponse | null>(null);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const updateWorkPlan = useUpdateWorkPlan(editingPlan?.id || "");
  const deleteWorkPlan = useDeleteWorkPlan();

  if (isLoading) {
    return <LoadingState label="Loading daftar penugasan..." />;
  }

  if (error || !workPlans) {
    return <ErrorState label="Gagal memuat daftar penugasan." />;
  }

  const employeeName = (id: string | null) => employees?.find((e) => e.id === id)?.full_name || "-";

  const openCreate = () => {
    setEditingPlan(null);
    setFormData(EMPTY_FORM);
    setIsModalOpen(true);
  };

  const openEdit = (plan: WorkPlanResponse) => {
    setEditingPlan(plan);
    setFormData({
      title: plan.title,
      description: plan.description || "",
      assignee_id: plan.assignee_id || "",
      planned_date: plan.planned_date || "",
      status: plan.status,
      member_ids: plan.members.map((m) => m.employee_id),
    });
    setIsModalOpen(true);
  };

  const toggleMember = (empId: string) => {
    setFormData((f) => ({
      ...f,
      member_ids: f.member_ids.includes(empId)
        ? f.member_ids.filter((id) => id !== empId)
        : [...f.member_ids, empId],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Backend menolak "" untuk field opsional bertipe UUID / date (422) — kirim hanya
    // field yang benar-benar diisi.
    const payload: WorkPlanCreatePayload = { title: formData.title.trim(), member_ids: formData.member_ids };
    if (formData.description.trim()) payload.description = formData.description.trim();
    if (formData.assignee_id) payload.assignee_id = formData.assignee_id;
    if (formData.planned_date) payload.planned_date = formData.planned_date;
    if (editingPlan) payload.status = formData.status;

    if (editingPlan) {
      await updateWorkPlan.mutateAsync(payload);
    } else {
      await createWorkPlan.mutateAsync(payload);
    }
    setIsModalOpen(false);
    setFormData(EMPTY_FORM);
    setEditingPlan(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteWorkPlan.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Plan</h1>
          <p className="mt-1 text-sm text-gray-500">Daftar penugasan dan rencana kerja lapangan.</p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
          <Button onClick={openCreate}>Buat Penugasan</Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchBar value={searchInput} onChange={(v) => { setSearchInput(v); setSkip(0); }} placeholder="Cari judul penugasan..." />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setSkip(0); }}
          className="rounded-md border border-gray-300 p-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          <option value="">Semua Status</option>
          <option value="DRAFT">Draft</option>
          <option value="ACTIVE">Active</option>
          <option value="COMPLETED">Completed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Judul</TableHeader>
              <TableHeader>Ketua Tim</TableHeader>
              <TableHeader>Tim</TableHeader>
              <TableHeader>Tanggal Direncanakan</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {workPlans.length === 0 ? (
              <EmptyTableRow colSpan={6} label="Belum ada data penugasan." />
            ) : (
              workPlans.map((plan) => (
                <TableRow key={plan.id}>
                  <TableCell>{plan.title}</TableCell>
                  <TableCell>{employeeName(plan.assignee_id)}</TableCell>
                  <TableCell>{plan.members.length > 0 ? `+${plan.members.length} anggota` : "-"}</TableCell>
                  <TableCell>{plan.planned_date || "-"}</TableCell>
                  <TableCell>
                    <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_BADGE[plan.status]}`}>
                      {plan.status}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => setDetailPlan(plan)} className="text-indigo-600 hover:underline text-sm">Detail</button>
                      <button onClick={() => openEdit(plan)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => setDeleteTarget(plan)} className="text-red-600 hover:underline text-sm">Hapus</button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <Pagination skip={skip} limit={PAGE_SIZE} currentCount={workPlans.length} onSkipChange={setSkip} />
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingPlan ? "Edit Penugasan" : "Buat Penugasan Baru"} size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Judul"
            required
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          />
          <TextArea
            label="Deskripsi"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
          <Select
            label="Ketua Tim (Opsional)"
            value={formData.assignee_id}
            onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value })}
          >
            <option value="">-- Tidak Ada / Kosong --</option>
            {employees?.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.full_name}
              </option>
            ))}
          </Select>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Anggota Tim Tambahan (Opsional)</label>
            <div className="max-h-40 overflow-y-auto rounded-md border border-gray-300 p-2 space-y-1">
              {employees?.filter((e) => e.id !== formData.assignee_id).map((emp) => (
                <label key={emp.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formData.member_ids.includes(emp.id)}
                    onChange={() => toggleMember(emp.id)}
                  />
                  {emp.full_name}
                </label>
              ))}
            </div>
          </div>

          <Input
            label="Tanggal Direncanakan (Opsional)"
            type="date"
            value={formData.planned_date}
            onChange={(e) => setFormData({ ...formData, planned_date: e.target.value })}
          />

          {editingPlan && (
            <Select label="Status" value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}>
              <option value="DRAFT">Draft</option>
              <option value="ACTIVE">Active</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </Select>
          )}

          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createWorkPlan.isPending || updateWorkPlan.isPending} />
        </form>
      </Modal>

      <DetailDrawer isOpen={!!detailPlan} onClose={() => setDetailPlan(null)} title={detailPlan?.title || "Detail Penugasan"}>
        {detailPlan && (
          <dl>
            <DetailField label="Deskripsi" value={detailPlan.description} />
            <DetailField label="Ketua Tim" value={employeeName(detailPlan.assignee_id)} />
            <DetailField
              label="Anggota Tim"
              value={detailPlan.members.length > 0 ? detailPlan.members.map((m) => employeeName(m.employee_id)).join(", ") : "-"}
            />
            <DetailField label="Tanggal Direncanakan" value={detailPlan.planned_date} />
            <DetailField label="Status" value={detailPlan.status} />
            <DetailField label="Jumlah Laporan Progres" value={detailPlan.progress_reports.length} />
          </dl>
        )}
      </DetailDrawer>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus penugasan "${deleteTarget?.title}"? Laporan progres terkait tetap tersimpan.`}
        isConfirming={deleteWorkPlan.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default WorkPlanPage;
