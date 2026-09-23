import { useState } from "react";
import {
  useVehicleBookings,
  useToolBorrows,
  useVehicleServices,
  useCreateVehicleBooking,
  useCreateToolBorrow,
  useCreateVehicleService,
  useApproveVehicleBooking,
  useDeleteVehicleBooking,
  useApproveToolBorrow,
  useDeleteToolBorrow,
  useUpdateVehicleService,
  useDeleteVehicleService,
} from "../../hooks/api/useLogbooks";
import { useVehicles, useItems } from "../../hooks/api/useLookups";
import { VehicleServiceResponse } from "../../types/logbook";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { LoadingState, EmptyTableRow } from "../../components/ui/QueryState";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  RETURNED: "bg-gray-100 text-gray-800",
};

/**
 * Halaman Logbook Operasional
 * Digunakan untuk mencatat peminjaman kendaraan, alat kerja, serta riwayat servis kendaraan.
 */
const LogbookPage = () => {
  const { user } = useAuth();
  const canApprove = user?.role === UserRole.PM || user?.role === UserRole.OM || user?.role === UserRole.ADMIN;

  const [activeTab, setActiveTab] = useState<"vehicles" | "tools" | "services">("vehicles");

  const { data: vehicles, isLoading: loadingV } = useVehicleBookings();
  const { data: tools, isLoading: loadingT } = useToolBorrows();
  const { data: services, isLoading: loadingS } = useVehicleServices();

  const { data: listVehicles } = useVehicles();
  const { data: listItems } = useItems();

  const createVehicle = useCreateVehicleBooking();
  const createTool = useCreateToolBorrow();
  const createService = useCreateVehicleService();
  const approveBooking = useApproveVehicleBooking();
  const deleteBooking = useDeleteVehicleBooking();
  const approveTool = useApproveToolBorrow();
  const deleteTool = useDeleteToolBorrow();
  const updateService = useUpdateVehicleService();
  const deleteService = useDeleteVehicleService();

  const [isVModalOpen, setIsVModalOpen] = useState(false);
  const [isTModalOpen, setIsTModalOpen] = useState(false);
  const [isSModalOpen, setIsSModalOpen] = useState(false);
  const [editingService, setEditingService] = useState<VehicleServiceResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ kind: "booking" | "tool" | "service"; id: string; label: string } | null>(null);

  const [vForm, setVForm] = useState({ vehicle_id: "", start_time: "", end_time: "", purpose: "", odometer_start: 0 });
  const [tForm, setTForm] = useState({ item_id: "", borrow_date: "", return_date: "", condition_borrow: "", quantity: 1 });
  const [sForm, setSForm] = useState({ vehicle_id: "", service_date: "", description: "", cost: 0, mechanic_name: "" });

  const isLoading = loadingV || loadingT || loadingS;

  const handleCreateV = async (e: React.FormEvent) => {
    e.preventDefault();
    await createVehicle.mutateAsync({
      ...vForm,
      start_time: new Date(vForm.start_time).toISOString(),
      end_time: new Date(vForm.end_time).toISOString()
    });
    setIsVModalOpen(false);
  };

  const handleCreateT = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTool.mutateAsync({
      ...tForm,
      borrow_date: new Date(tForm.borrow_date).toISOString(),
      return_date: tForm.return_date ? new Date(tForm.return_date).toISOString() : undefined,
    });
    setIsTModalOpen(false);
  };

  const handleCreateS = async (e: React.FormEvent) => {
    e.preventDefault();
    await createService.mutateAsync({
      ...sForm,
      service_date: new Date(sForm.service_date).toISOString()
    });
    setIsSModalOpen(false);
  };

  const handleUpdateService = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingService) return;
    await updateService.mutateAsync({ id: editingService.id, payload: sForm });
    setEditingService(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    if (deleteTarget.kind === "booking") await deleteBooking.mutateAsync(deleteTarget.id);
    else if (deleteTarget.kind === "tool") await deleteTool.mutateAsync(deleteTarget.id);
    else await deleteService.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  if (isLoading) {
    return <LoadingState label="Loading data logbook..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Logbook Operasional</h1>
          <p className="mt-1 text-sm text-gray-500">Manajemen aset operasional (Kendaraan & Alat Kerja).</p>
        </div>
        <div className="space-x-2">
          {activeTab === "vehicles" && (
            <Button onClick={() => setIsVModalOpen(true)}>+ Pinjam Kendaraan</Button>
          )}
          {activeTab === "tools" && (
            <Button onClick={() => setIsTModalOpen(true)}>+ Pinjam Alat Kerja</Button>
          )}
          {activeTab === "services" && (
            <Button onClick={() => setIsSModalOpen(true)}>+ Catat Servis</Button>
          )}
        </div>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("vehicles")}
            className={`${activeTab === "vehicles" ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm`}
          >
            Kendaraan
          </button>
          <button
            onClick={() => setActiveTab("tools")}
            className={`${activeTab === "tools" ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm`}
          >
            Alat Kerja
          </button>
          <button
            onClick={() => setActiveTab("services")}
            className={`${activeTab === "services" ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm`}
          >
            Riwayat Servis
          </button>
        </nav>
      </div>

      {activeTab === "vehicles" && (
        <div className="bg-white shadow rounded-lg border">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Waktu Pinjam</TableHeader>
                <TableHeader>Tujuan</TableHeader>
                <TableHeader>Status</TableHeader>
                <TableHeader>Aksi</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {!vehicles || vehicles.length === 0 ? (
                <EmptyTableRow colSpan={4} label="Belum ada peminjaman kendaraan." />
              ) : (
                vehicles.map(v => (
                  <TableRow key={v.id}>
                    <TableCell>{new Date(v.start_time).toLocaleString()}</TableCell>
                    <TableCell>{v.purpose}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_BADGE[v.approval_status]}`}>{v.approval_status}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        {canApprove && v.approval_status === "PENDING" && (
                          <>
                            <button onClick={() => approveBooking.mutate({ id: v.id, status: "APPROVED" })} className="text-green-600 hover:underline text-sm">Setujui</button>
                            <button onClick={() => approveBooking.mutate({ id: v.id, status: "REJECTED" })} className="text-red-600 hover:underline text-sm">Tolak</button>
                          </>
                        )}
                        <button onClick={() => setDeleteTarget({ kind: "booking", id: v.id, label: v.purpose })} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {activeTab === "tools" && (
        <div className="bg-white shadow rounded-lg border">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Tgl Pinjam</TableHeader>
                <TableHeader>Qty</TableHeader>
                <TableHeader>Kondisi</TableHeader>
                <TableHeader>Status</TableHeader>
                <TableHeader>Aksi</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {!tools || tools.length === 0 ? (
                <EmptyTableRow colSpan={5} label="Belum ada peminjaman alat kerja." />
              ) : (
                tools.map(t => (
                  <TableRow key={t.id}>
                    <TableCell>{new Date(t.borrow_date).toLocaleDateString()}</TableCell>
                    <TableCell>{t.quantity}</TableCell>
                    <TableCell>{t.condition_borrow}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_BADGE[t.approval_status]}`}>{t.approval_status}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        {canApprove && t.approval_status === "PENDING" && (
                          <>
                            <button onClick={() => approveTool.mutate({ id: t.id, status: "APPROVED" })} className="text-green-600 hover:underline text-sm">Setujui</button>
                            <button onClick={() => approveTool.mutate({ id: t.id, status: "REJECTED" })} className="text-red-600 hover:underline text-sm">Tolak</button>
                          </>
                        )}
                        <button onClick={() => setDeleteTarget({ kind: "tool", id: t.id, label: t.condition_borrow })} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {activeTab === "services" && (
        <div className="bg-white shadow rounded-lg border">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Tanggal</TableHeader>
                <TableHeader>Mekanik</TableHeader>
                <TableHeader>Biaya</TableHeader>
                <TableHeader>Deskripsi</TableHeader>
                <TableHeader>Aksi</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {!services || services.length === 0 ? (
                <EmptyTableRow colSpan={5} label="Belum ada riwayat servis." />
              ) : (
                services.map(s => (
                  <TableRow key={s.id}>
                    <TableCell>{new Date(s.service_date).toLocaleDateString()}</TableCell>
                    <TableCell>{s.mechanic_name}</TableCell>
                    <TableCell>Rp {s.cost.toLocaleString()}</TableCell>
                    <TableCell>{s.description}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={() => {
                            setEditingService(s);
                            setSForm({ vehicle_id: s.vehicle_id, service_date: s.service_date.slice(0, 10), description: s.description, cost: s.cost, mechanic_name: s.mechanic_name });
                          }}
                          className="text-indigo-600 hover:underline text-sm"
                        >
                          Edit
                        </button>
                        <button onClick={() => setDeleteTarget({ kind: "service", id: s.id, label: s.description })} className="text-red-600 hover:underline text-sm">Hapus</button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Modal isOpen={isVModalOpen} onClose={() => setIsVModalOpen(false)} title="Peminjaman Kendaraan">
        <form onSubmit={handleCreateV} className="space-y-4">
          <Select
            label="Kendaraan"
            required
            value={vForm.vehicle_id}
            onChange={e => setVForm({ ...vForm, vehicle_id: e.target.value })}
          >
            <option value="">-- Pilih Kendaraan --</option>
            {listVehicles?.map(v => (
              <option key={v.id} value={v.id}>{v.license_plate} - {v.name}</option>
            ))}
          </Select>
          <div className="flex space-x-2">
            <div className="flex-1">
              <Input label="Mulai" required type="datetime-local" value={vForm.start_time} onChange={e => setVForm({ ...vForm, start_time: e.target.value })} />
            </div>
            <div className="flex-1">
              <Input label="Selesai" required type="datetime-local" value={vForm.end_time} onChange={e => setVForm({ ...vForm, end_time: e.target.value })} />
            </div>
          </div>
          <Input label="Tujuan" required value={vForm.purpose} onChange={e => setVForm({ ...vForm, purpose: e.target.value })} />
          <Input
            label="Odometer Awal (km)"
            required
            type="number"
            min="0"
            value={vForm.odometer_start}
            onChange={e => setVForm({ ...vForm, odometer_start: parseInt(e.target.value) })}
          />
          <ModalFooter onCancel={() => setIsVModalOpen(false)} isSubmitting={createVehicle.isPending} />
        </form>
      </Modal>

      <Modal isOpen={isTModalOpen} onClose={() => setIsTModalOpen(false)} title="Peminjaman Alat Kerja">
        <form onSubmit={handleCreateT} className="space-y-4">
          <Select
            label="Alat Kerja / Item"
            required
            value={tForm.item_id}
            onChange={e => setTForm({ ...tForm, item_id: e.target.value })}
          >
            <option value="">-- Pilih Alat --</option>
            {listItems?.map(i => (
              <option key={i.id} value={i.id}>{i.name} ({i.code}) — stok {i.stock}</option>
            ))}
          </Select>
          <div className="flex space-x-2">
            <div className="flex-1">
              <Input label="Dipinjam" required type="datetime-local" value={tForm.borrow_date} onChange={e => setTForm({ ...tForm, borrow_date: e.target.value })} />
            </div>
            <div className="flex-1">
              <Input label="Ekspektasi Kembali" type="datetime-local" value={tForm.return_date} onChange={e => setTForm({ ...tForm, return_date: e.target.value })} />
            </div>
          </div>
          <Input label="Kondisi Saat Dipinjam" required value={tForm.condition_borrow} onChange={e => setTForm({ ...tForm, condition_borrow: e.target.value })} />
          <Input
            label="Jumlah (Qty)"
            required
            type="number"
            min="1"
            value={tForm.quantity}
            onChange={e => setTForm({ ...tForm, quantity: parseInt(e.target.value) })}
          />
          <ModalFooter onCancel={() => setIsTModalOpen(false)} isSubmitting={createTool.isPending} />
        </form>
      </Modal>

      <Modal isOpen={isSModalOpen} onClose={() => setIsSModalOpen(false)} title="Catat Servis Kendaraan">
        <form onSubmit={handleCreateS} className="space-y-4">
          <Select
            label="Kendaraan"
            required
            value={sForm.vehicle_id}
            onChange={e => setSForm({ ...sForm, vehicle_id: e.target.value })}
          >
            <option value="">-- Pilih Kendaraan --</option>
            {listVehicles?.map(v => (
              <option key={v.id} value={v.id}>{v.license_plate} - {v.name}</option>
            ))}
          </Select>
          <Input label="Tanggal Servis" required type="date" value={sForm.service_date} onChange={e => setSForm({ ...sForm, service_date: e.target.value })} />
          <Input label="Nama Mekanik / Bengkel" required value={sForm.mechanic_name} onChange={e => setSForm({ ...sForm, mechanic_name: e.target.value })} />
          <Input label="Deskripsi Perbaikan" required value={sForm.description} onChange={e => setSForm({ ...sForm, description: e.target.value })} />
          <Input
            label="Biaya (Rp)"
            required
            type="number"
            min="0"
            value={sForm.cost}
            onChange={e => setSForm({ ...sForm, cost: parseInt(e.target.value) })}
          />
          <ModalFooter onCancel={() => setIsSModalOpen(false)} isSubmitting={createService.isPending} />
        </form>
      </Modal>

      <Modal isOpen={!!editingService} onClose={() => setEditingService(null)} title="Edit Servis Kendaraan">
        <form onSubmit={handleUpdateService} className="space-y-4">
          <Input label="Tanggal Servis" required type="date" value={sForm.service_date} onChange={e => setSForm({ ...sForm, service_date: e.target.value })} />
          <Input label="Nama Mekanik / Bengkel" required value={sForm.mechanic_name} onChange={e => setSForm({ ...sForm, mechanic_name: e.target.value })} />
          <Input label="Deskripsi Perbaikan" required value={sForm.description} onChange={e => setSForm({ ...sForm, description: e.target.value })} />
          <Input
            label="Biaya (Rp)"
            required
            type="number"
            min="0"
            value={sForm.cost}
            onChange={e => setSForm({ ...sForm, cost: parseInt(e.target.value) })}
          />
          <ModalFooter onCancel={() => setEditingService(null)} isSubmitting={updateService.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus data "${deleteTarget?.label}"?`}
        isConfirming={deleteBooking.isPending || deleteTool.isPending || deleteService.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default LogbookPage;
