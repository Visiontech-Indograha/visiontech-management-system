import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock } from "@/components/molecules/ListBlock";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField } from "@/components/molecules/Field";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { useAddressAction, type Address } from "@/services/employeeService";

const EMPTY = { address_line: "", city: "", postal_code: "" };

/** Kelola alamat karyawan: tambah/ubah/hapus (inline, ringkas). */
export function EmployeeAddressesPanel({
  employeeId,
  addresses,
  canEdit,
}: {
  employeeId: string;
  addresses: Address[];
  canEdit: boolean;
}) {
  const action = useAddressAction(employeeId);
  const [editing, setEditing] = useState<string | null>(null); // "new" = alamat baru
  const [form, setForm] = useState(EMPTY);
  const [deleteTarget, setDeleteTarget] = useState<Address | null>(null);

  const open = (a?: Address) => {
    setEditing(a ? a.address_id : "new");
    setForm(a ? { address_line: a.address_line, city: a.city, postal_code: a.postal_code } : EMPTY);
  };

  const run = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn();
      toast.success(done);
      setEditing(null);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const save = () => {
    const line = form.address_line.trim();
    const city = form.city.trim();
    const postal = form.postal_code.trim();

    if (!line || !city || !postal) {
      toast.error("Alamat, kota, dan kode pos wajib diisi lengkap.");
      return;
    }
    if (postal.length < 3 || postal.length > 10) {
      toast.error("Kode pos harus antara 3 hingga 10 karakter.");
      return;
    }

    return run(
      () =>
        editing === "new"
          ? action.mutateAsync({ kind: "add", body: { address_line: line, city, postal_code: postal } })
          : action.mutateAsync({ kind: "update", id: editing ?? "", body: { address_line: line, city, postal_code: postal } }),
      "Alamat disimpan.",
    );
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await action.mutateAsync({ kind: "delete", id: deleteTarget.address_id });
      toast.success("Alamat berhasil dihapus.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="mb-8 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-4">
      <div className="mb-2 flex items-center justify-between">
        <SectionTitle>Alamat</SectionTitle>
        {canEdit && editing === null && (
          <ActionButton variant="outline" size="sm" onClick={() => open()}>
            Tambah alamat
          </ActionButton>
        )}
      </div>
      {addresses.length === 0 && editing === null && (
        <TextBlock className="text-sm text-mist">Belum ada alamat.</TextBlock>
      )}
      <ListBlock className="text-sm">
        {addresses.map((a) => (
          <div key={a.address_id} className="flex items-start justify-between gap-3 border-b border-line py-2 last:border-0">
            <TextBlock>{`${a.address_line}, ${a.city} ${a.postal_code}`}</TextBlock>
            {canEdit && editing === null && (
              <div className="flex gap-1">
                <ActionButton variant="ghost" size="sm" onClick={() => open(a)}>
                  Ubah
                </ActionButton>
                <ActionButton
                  variant="ghost"
                  size="sm"
                  disabled={action.isPending}
                  onClick={() => setDeleteTarget(a)}
                >
                  Hapus
                </ActionButton>
              </div>
            )}
          </div>
        ))}
      </ListBlock>
      {editing !== null && (
        <div className="mt-3">
          <TextField
            label="Alamat"
            value={form.address_line}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, address_line: e.target.value })}
          />
          <TextField
            label="Kota"
            value={form.city}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, city: e.target.value })}
          />
          <TextField
            label="Kode pos"
            value={form.postal_code}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, postal_code: e.target.value })}
          />
          <div className="flex justify-end gap-2">
            <ActionButton variant="outline" size="sm" onClick={() => setEditing(null)}>
              Batal
            </ActionButton>
            <ActionButton size="sm" disabled={action.isPending} onClick={save}>
              Simpan
            </ActionButton>
          </div>
        </div>
      )}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Hapus Alamat Karyawan?"
        message={`Apakah Anda yakin ingin menghapus alamat "${deleteTarget?.address_line ?? ""}"?`}
        confirmLabel="Hapus Alamat"
        danger
        busy={action.isPending}
        onConfirm={confirmDelete}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  );
}
