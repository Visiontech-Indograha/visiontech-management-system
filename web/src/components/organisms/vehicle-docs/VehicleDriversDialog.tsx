import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useSession } from "@/stores/sessionStore";
import { useEmployees } from "@/services/employeeService";
import { useAddVehicleDriver, useEndVehicleDriver, useVehicleDrivers, type VehicleDriver } from "@/services/vehicleDocumentService";

/** Pengemudi kendaraan: daftar, tambah (karyawan aktif), dan akhiri penugasan. */
export function VehicleDriversDialog({ vehicleId, plate, onClose }: { vehicleId: string; plate: string; onClose: () => void }) {
  const canManage = (useSession().me?.permissions ?? []).includes("manage:vehicle_documents");
  const drivers = useVehicleDrivers(vehicleId);
  const add = useAddVehicleDriver(vehicleId);
  const end = useEndVehicleDriver(vehicleId);
  const [search, setSearch] = useState("");
  const q = useDebouncedValue(search.trim(), 300);
  const employees = useEmployees({ status: "active", page: 1, size: 50, q: q || undefined });
  const [employeeId, setEmployeeId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ending, setEnding] = useState<VehicleDriver | null>(null);
  const current = (drivers.data ?? []).filter((d) => !d.selesai_on);

  const onAdd = async () => {
    if (!employeeId) return setError("Pilih karyawan dulu.");
    setError(null);
    try {
      await add.mutateAsync(employeeId);
      toast.success("Pengemudi ditambahkan.");
      setEmployeeId("");
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  const onEnd = async () => {
    if (!ending) return;
    try {
      await end.mutateAsync(ending.vehicle_driver_id);
      toast.success("Penugasan pengemudi diakhiri.");
    } catch (err) {
      setError(errorMessage(err));
    }
    setEnding(null);
  };
  return (
    <VmsDialog open title={`Pengemudi ${plate}`} onClose={onClose} footer={<ActionButton variant="outline" onClick={onClose}>Tutup</ActionButton>}>
      <QueryState query={drivers} errorText="Daftar pengemudi tidak dapat dimuat." empty={current.length === 0} emptyText="Belum ada pengemudi tercatat.">
        <ListBlock className="mb-4 divide-y divide-line">
          {current.map((d) => (
            <ListEntry key={d.vehicle_driver_id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <TextBlock as="span" className="font-medium">{d.employee_name}</TextBlock>
              <TextBlock as="span" className="text-mist">sejak {formatDate(d.mulai_on)}</TextBlock>
              {canManage && <ActionButton size="sm" variant="outline" onClick={() => setEnding(d)}>Akhiri</ActionButton>}
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
      {canManage && (
        <div>
          <TextField label="Cari karyawan" value={search} maxLength={100} onChange={(e) => setSearch(e.target.value)} />
          <SelectField label="Tambah pengemudi" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} error={error ?? undefined}>
            <ControlOption value="">Pilih karyawan</ControlOption>
            {employees.data?.items.map((e) => <ControlOption key={e.employee_id} value={e.employee_id}>{e.full_name}</ControlOption>)}
          </SelectField>
          <ActionButton onClick={onAdd} pending={add.isPending} pendingText="Menyimpan...">Tambah pengemudi</ActionButton>
        </div>
      )}
      <ConfirmDialog open={!!ending} title="Akhiri penugasan?" message={`${ending?.employee_name ?? ""} tidak lagi tercatat sebagai pengemudi ${plate}.`} confirmLabel="Ya, akhiri" busy={end.isPending} danger onConfirm={onEnd} onClose={() => setEnding(null)} />
    </VmsDialog>
  );
}
