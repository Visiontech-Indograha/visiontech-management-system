import { useState } from "react";
import { titleHooks, workCategoryHooks, productCategoryHooks, ceCategoryHooks, NamedLookup } from "../../hooks/api/useMaster";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, TextArea } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import toast from "react-hot-toast";

const TABS = [
  { key: "titles", label: "Jabatan", hooks: titleHooks },
  { key: "work-categories", label: "Kategori Pekerjaan", hooks: workCategoryHooks },
  { key: "product-categories", label: "Kategori Produk", hooks: productCategoryHooks },
  { key: "ce-categories", label: "Kategori Pengalaman", hooks: ceCategoryHooks },
] as const;

const SystemSetupPage = () => {
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("titles");
  const active = TABS.find((t) => t.key === tab)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">System Setup</h1>
        <p className="mt-1 text-sm text-gray-500">Kelola data master referensi aplikasi.</p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex flex-wrap gap-x-8">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`${tab === t.key ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"} whitespace-nowrap border-b-2 px-1 pb-4 text-sm font-medium`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <LookupTable key={active.key} label={active.label} hooks={active.hooks} />
    </div>
  );
};

const LookupTable = ({ label, hooks }: { label: string; hooks: (typeof TABS)[number]["hooks"] }) => {
  const { data: items, isLoading, error } = hooks.useList();
  const createMutation = hooks.useCreate();
  const updateMutation = hooks.useUpdate();
  const deleteMutation = hooks.useDelete();
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.HR_HES;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<NamedLookup | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<NamedLookup | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", description: "" });
    setIsModalOpen(true);
  };

  const openEdit = (item: NamedLookup) => {
    setEditing(item);
    setForm({ name: item.name, description: item.description || "" });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { name: form.name, description: form.description || undefined };
      if (editing) {
        await updateMutation.mutateAsync({ id: editing.id, payload });
      } else {
        await createMutation.mutateAsync(payload);
      }
      setIsModalOpen(false);
    } catch {
      // Error sudah ditampilkan oleh interceptor global di lib/api.ts
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
    } catch {
      toast.error("Gagal menghapus, mungkin masih dipakai data lain.");
    }
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label={`Loading ${label}...`} />;
  if (error) return <ErrorState label={`Gagal memuat ${label}.`} />;

  return (
    <div className="space-y-4">
      {canWrite && (
        <div className="flex justify-end">
          <Button onClick={openCreate}>+ Tambah {label}</Button>
        </div>
      )}

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Nama</TableHeader>
              <TableHeader>Deskripsi</TableHeader>
              {canWrite && <TableHeader>Aksi</TableHeader>}
            </TableRow>
          </TableHead>
          <TableBody>
            {!items || items.length === 0 ? (
              <EmptyTableRow colSpan={canWrite ? 3 : 2} label={`Belum ada data ${label}.`} />
            ) : (
              items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.description || "-"}</TableCell>
                  {canWrite && (
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => openEdit(item)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                        <button onClick={() => setDeleteTarget(item)} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? `Edit ${label}` : `Tambah ${label}`}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Nama"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
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
        message={`Hapus "${deleteTarget?.name}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default SystemSetupPage;
