import { useState } from "react";
import {
  useMasterVehicles, useCreateVehicle, useUpdateVehicle, useDeleteVehicle, MasterVehicle,
  useMasterItems, useCreateItem, useUpdateItem, useDeleteItem, MasterItem,
} from "../../hooks/api/useMaster";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { SearchBar } from "../../components/ui/SearchBar";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";

const InventoryPage = () => {
  const [tab, setTab] = useState<"vehicles" | "items">("vehicles");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
        <p className="mt-1 text-sm text-gray-500">Kelola master kendaraan dan alat perusahaan.</p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(["vehicles", "items"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`${tab === t ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"} whitespace-nowrap border-b-2 px-1 pb-4 text-sm font-medium`}
            >
              {t === "vehicles" ? "Kendaraan" : "Alat"}
            </button>
          ))}
        </nav>
      </div>

      {tab === "vehicles" ? <VehicleTab /> : <ItemTab />}
    </div>
  );
};

const VEHICLE_STATUS = ["AVAILABLE", "IN_USE", "MAINTENANCE"];
const EMPTY_VEHICLE = { name: "", license_plate: "", type: "", status: "AVAILABLE" };

const VehicleTab = () => {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 400);
  const { data: vehicles, isLoading, error } = useMasterVehicles({ q: debouncedSearch || undefined });
  const createMutation = useCreateVehicle();
  const updateMutation = useUpdateVehicle();
  const deleteMutation = useDeleteVehicle();
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.OM;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<MasterVehicle | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterVehicle | null>(null);
  const [form, setForm] = useState(EMPTY_VEHICLE);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_VEHICLE);
    setIsModalOpen(true);
  };

  const openEdit = (v: MasterVehicle) => {
    setEditing(v);
    setForm({ name: v.name, license_plate: v.license_plate, type: v.type || "", status: v.status });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { ...form, type: form.type || undefined };
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
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label="Loading kendaraan..." />;
  if (error) return <ErrorState label="Gagal memuat data kendaraan." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchBar value={search} onChange={setSearch} placeholder="Cari nama / plat nomor..." />
        {canWrite && <Button onClick={openCreate}>+ Tambah Kendaraan</Button>}
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Nama</TableHeader>
              <TableHeader>Plat Nomor</TableHeader>
              <TableHeader>Tipe</TableHeader>
              <TableHeader>Status</TableHeader>
              {canWrite && <TableHeader>Aksi</TableHeader>}
            </TableRow>
          </TableHead>
          <TableBody>
            {!vehicles || vehicles.length === 0 ? (
              <EmptyTableRow colSpan={canWrite ? 5 : 4} label="Belum ada data kendaraan." />
            ) : (
              vehicles.map((v) => (
                <TableRow key={v.id}>
                  <TableCell>{v.name}</TableCell>
                  <TableCell>{v.license_plate}</TableCell>
                  <TableCell>{v.type || "-"}</TableCell>
                  <TableCell>
                    <span className="inline-flex rounded-full bg-blue-100 px-2 text-xs font-semibold leading-5 text-blue-800">
                      {v.status}
                    </span>
                  </TableCell>
                  {canWrite && (
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => openEdit(v)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                        <button onClick={() => setDeleteTarget(v)} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? "Edit Kendaraan" : "Tambah Kendaraan"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Nama" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="Plat Nomor" required value={form.license_plate} onChange={(e) => setForm({ ...form, license_plate: e.target.value })} />
          <Input label="Tipe (Opsional)" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} />
          <Select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {VEHICLE_STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createMutation.isPending || updateMutation.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus kendaraan "${deleteTarget?.name}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

const EMPTY_ITEM = { name: "", code: "", type: "", stock: 0 };

const ItemTab = () => {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 400);
  const { data: items, isLoading, error } = useMasterItems({ q: debouncedSearch || undefined });
  const createMutation = useCreateItem();
  const updateMutation = useUpdateItem();
  const deleteMutation = useDeleteItem();
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.OM;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<MasterItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterItem | null>(null);
  const [form, setForm] = useState(EMPTY_ITEM);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_ITEM);
    setIsModalOpen(true);
  };

  const openEdit = (it: MasterItem) => {
    setEditing(it);
    setForm({ name: it.name, code: it.code, type: it.type || "", stock: it.stock });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { ...form, type: form.type || undefined, stock: Number(form.stock) };
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
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label="Loading alat..." />;
  if (error) return <ErrorState label="Gagal memuat data alat." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchBar value={search} onChange={setSearch} placeholder="Cari nama / kode..." />
        {canWrite && <Button onClick={openCreate}>+ Tambah Alat</Button>}
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Nama</TableHeader>
              <TableHeader>Kode</TableHeader>
              <TableHeader>Tipe</TableHeader>
              <TableHeader>Stok</TableHeader>
              {canWrite && <TableHeader>Aksi</TableHeader>}
            </TableRow>
          </TableHead>
          <TableBody>
            {!items || items.length === 0 ? (
              <EmptyTableRow colSpan={canWrite ? 5 : 4} label="Belum ada data alat." />
            ) : (
              items.map((it) => (
                <TableRow key={it.id}>
                  <TableCell>{it.name}</TableCell>
                  <TableCell>{it.code}</TableCell>
                  <TableCell>{it.type || "-"}</TableCell>
                  <TableCell>{it.stock}</TableCell>
                  {canWrite && (
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => openEdit(it)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                        <button onClick={() => setDeleteTarget(it)} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? "Edit Alat" : "Tambah Alat"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Nama" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="Kode" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          <Input label="Tipe (Opsional)" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} />
          <Input
            label="Stok"
            required
            type="number"
            min={0}
            value={form.stock}
            onChange={(e) => setForm({ ...form, stock: Number(e.target.value) })}
          />
          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createMutation.isPending || updateMutation.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus alat "${deleteTarget?.name}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default InventoryPage;
