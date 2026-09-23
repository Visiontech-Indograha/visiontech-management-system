import { useState } from "react";
import {
  useCompanyExperiences,
  useCreateCompanyExperience,
  useUpdateCompanyExperience,
  useDeleteCompanyExperience,
  useCategoryCE,
} from "../../hooks/api/usePortofolio";
import { CompanyExperience } from "../../types/portofolio";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select, TextArea } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import toast from "react-hot-toast";

const EMPTY_FORM = { project_name: "", client_name: "", category_ce_id: "", start_date: "", end_date: "", description: "" };

const PortofolioPage = () => {
  const { data: experiences, isLoading, error } = useCompanyExperiences();
  const { data: categories } = useCategoryCE();
  const createMutation = useCreateCompanyExperience();
  const updateMutation = useUpdateCompanyExperience();
  const deleteMutation = useDeleteCompanyExperience();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<CompanyExperience | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CompanyExperience | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setIsModalOpen(true);
  };

  const openEdit = (exp: CompanyExperience) => {
    setEditing(exp);
    setForm({
      project_name: exp.project_name,
      client_name: exp.client_name,
      category_ce_id: exp.category_ce_id,
      start_date: exp.start_date,
      end_date: exp.end_date || "",
      description: exp.description || "",
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.category_ce_id) {
      toast.error("Silakan pilih kategori proyek");
      return;
    }
    try {
      const payload = { ...form, end_date: form.end_date || undefined };
      if (editing) {
        await updateMutation.mutateAsync({ id: editing.id, data: payload });
        toast.success("Portofolio berhasil diperbarui");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("Portofolio berhasil ditambahkan");
      }
      setIsModalOpen(false);
      setForm(EMPTY_FORM);
      setEditing(null);
    } catch {
      // Error sudah ditampilkan oleh interceptor global di lib/api.ts
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    toast.success("Portofolio berhasil dihapus");
    setDeleteTarget(null);
  };

  if (isLoading) {
    return <LoadingState label="Loading portofolio..." />;
  }

  if (error) {
    return <ErrorState label="Gagal memuat data portofolio." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portofolio Perusahaan</h1>
          <p className="mt-1 text-sm text-gray-500">Kelola riwayat proyek (Company Experience).</p>
        </div>
        <Button onClick={openCreate}>+ Tambah Proyek</Button>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200 p-4">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Nama Proyek</TableHeader>
              <TableHeader>Klien</TableHeader>
              <TableHeader>Mulai</TableHeader>
              <TableHeader>Selesai</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {!experiences || experiences.length === 0 ? (
              <EmptyTableRow colSpan={5} label="Belum ada data portofolio." />
            ) : (
              experiences.map((exp) => (
                <TableRow key={exp.id}>
                  <TableCell>{exp.project_name}</TableCell>
                  <TableCell>{exp.client_name}</TableCell>
                  <TableCell>{exp.start_date}</TableCell>
                  <TableCell>{exp.end_date || "Berjalan"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => openEdit(exp)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => setDeleteTarget(exp)} className="text-red-600 hover:underline text-sm">Hapus</button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? "Edit Portofolio" : "Tambah Portofolio"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Nama Proyek"
            required
            value={form.project_name}
            onChange={(e) => setForm({ ...form, project_name: e.target.value })}
          />
          <Input
            label="Nama Klien"
            required
            value={form.client_name}
            onChange={(e) => setForm({ ...form, client_name: e.target.value })}
          />
          <Select
            label="Kategori Proyek"
            required
            value={form.category_ce_id}
            onChange={(e) => setForm({ ...form, category_ce_id: e.target.value })}
          >
            <option value="" disabled>Pilih Kategori</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </Select>
          <Input
            label="Tanggal Mulai"
            required
            type="date"
            value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })}
          />
          <Input
            label="Tanggal Selesai (Opsional)"
            type="date"
            value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })}
          />
          <TextArea
            label="Deskripsi (Opsional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createMutation.isPending || updateMutation.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus portofolio "${deleteTarget?.project_name}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default PortofolioPage;
