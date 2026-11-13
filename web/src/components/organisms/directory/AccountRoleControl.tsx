import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { RoleSelectField } from "@/components/molecules/RoleSelectField";
import { FIELD_ROLE_LABEL, PRIMARY_ROLE_LABEL, type PrimaryRole } from "@/services/employeeService";

/**
 * Pilih peran utama akun. Super Admin boleh semua peran; HR hanya Ketua tim / Karyawan lapangan.
 * Mengubah peran mengeluarkan sesi orang itu, jadi selalu minta konfirmasi dulu.
 */
export function AccountRoleControl({ current, superAdmin, busy, error, onConfirm }: {
  current: PrimaryRole;
  superAdmin: boolean;
  busy: boolean;
  error: string | null;
  onConfirm: (role: PrimaryRole) => Promise<boolean>;
}) {
  const [chosen, setChosen] = useState<PrimaryRole | null>(null);
  const [asking, setAsking] = useState(false);
  const value = chosen ?? current;
  const options: Record<string, string> = superAdmin ? PRIMARY_ROLE_LABEL : FIELD_ROLE_LABEL;

  const confirm = async () => {
    if (await onConfirm(value)) {
      setAsking(false);
      setChosen(null);
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="min-w-48">
        <RoleSelectField
          label="Peran utama"
          value={value}
          options={options}
          onChange={(v) => setChosen(v as PrimaryRole)}
        />
      </div>
      <ActionButton variant="outline" disabled={busy || value === current} onClick={() => setAsking(true)}>
        Simpan peran
      </ActionButton>
      <ConfirmDialog
        open={asking}
        title="Ubah peran utama?"
        message={`Peran akun ini akan menjadi ${PRIMARY_ROLE_LABEL[value]}. Semua sesi orang ini akan keluar dan ia harus masuk lagi.`}
        confirmLabel="Ya, ubah peran"
        busy={busy}
        error={error}
        onConfirm={confirm}
        onClose={() => setAsking(false)}
      />
    </div>
  );
}
