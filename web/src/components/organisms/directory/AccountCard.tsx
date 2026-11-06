import { useState } from "react";
import { toast } from "sonner";
import { TextField } from "@/components/molecules/Field";
import { RoleSelectField } from "@/components/molecules/RoleSelectField";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useSession } from "@/stores/sessionStore";
import {
  FIELD_ROLE_LABEL,
  useAccount,
  useAccountAction,
  useDeleteAccount,
  type Employee,
  type FieldRole,
} from "@/services/employeeService";
import { DeleteConfirmButton } from "@/components/organisms/DeleteConfirmButton";
import { Pill } from "@/components/molecules/Pill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { AccountDevicesAdmin } from "@/components/organisms/directory/AccountDevicesAdmin";
import { AccountLoginEditForm } from "@/components/organisms/directory/AccountLoginEditForm";

/**
 * M1-01 · HR/admin mengelola akun login karyawan: buat akun, reset password, buka kunci, ganti email,
 * kelola perangkat yang masuk, nonaktifkan/aktifkan, dan hapus akun (SUPER_ADMIN, di zona berbahaya).
 * Sandi sementara ditampilkan SEKALI di sini — sampaikan ke karyawan, lalu minta diganti di
 * "Akun & keamanan" setelah masuk.
 */
export function AccountCard({ employee }: { employee: Employee }) {
  const account = useAccount(employee.employee_id);
  const action = useAccountAction(employee.employee_id);
  const deleteAccount = useDeleteAccount(employee.employee_id);
  const [login, setLogin] = useState(employee.email ?? "");
  const [peranBaru, setPeranBaru] = useState<FieldRole>("EMPLOYEE");
  const [peranAkun, setPeranAkun] = useState<FieldRole | null>(null);
  const [issued, setIssued] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Peran lapangan hanya bisa dipilih HR/SUPER_ADMIN (keduanya memegang manage:users); API tetap memeriksa.
  const permissions = useSession().me?.permissions ?? [];
  const canSetRole = permissions.includes("manage:users");
  // Hapus akun hanya untuk SUPER_ADMIN (delete:any); API tetap memeriksa.
  const canDelete = permissions.includes("delete:any");

  const run = async (
    a: Parameters<typeof action.mutateAsync>[0],
    done: string,
  ) => {
    setError(null);
    try {
      const res = await action.mutateAsync(a);
      if ("temporary_password" in res && typeof res.temporary_password === "string") setIssued(res.temporary_password);
      toast.success(done);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const a = account.data;
  const roleAkun: FieldRole | null =
    a?.system_role === "EMPLOYEE" || a?.system_role === "TEAM_LEADER" ? a.system_role : null;
  const peranDipilih = peranAkun;
  const terkunci = !!a?.locked_until && new Date(a.locked_until) > new Date();
  return (
    <section aria-label="Akun login" className="mb-8 max-w-xl">
      <SectionTitle>Akun login</SectionTitle>
      <div className="rounded-panel border border-line bg-surface px-5 py-4 text-sm shadow-card">
        {account.isPending && <LoadingBar className="h-4 w-2/3" />}
        {account.isError && (
          <TextBlock className="text-danger">Status akun tidak dapat dimuat.</TextBlock>
        )}
        {error && (
          <TextBlock
            role="alert"
            className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-danger"
          >
            {error}
          </TextBlock>
        )}
        {issued && (
          <div
            role="status"
            className="mb-3 rounded-control bg-brand-50 px-3 py-2"
          >
            <TextBlock as="span">Sandi sementara (hanya ditampilkan sekali): </TextBlock>
            <TextBlock as="code" className="select-all font-mono font-semibold">{issued}</TextBlock>
            <TextBlock className="mt-1 text-caption text-mist">
              Sampaikan langsung ke karyawan; minta diganti setelah masuk.
            </TextBlock>
          </div>
        )}
        {a && !a.exists && (
          <div className="flex flex-col gap-3">
            <TextBlock className="text-mist">Karyawan ini belum punya akun login.</TextBlock>
            {employee.offboarding_status !== "offboarded" && (
              <>
                <TextField
                  label="Email login"
                  type="email"
                  value={login}
                  onChange={(e) => setLogin(e.target.value)}
                />
                {canSetRole && (
                  <RoleSelectField
                    label="Peran"
                    value={peranBaru}
                    options={FIELD_ROLE_LABEL}
                    onChange={(v) => setPeranBaru(v as FieldRole)}
                  />
                )}
                <ActionButton
                  className="self-start"
                  disabled={action.isPending || !login.trim()}
                  onClick={() =>
                    run(
                      { kind: "create", login: login.trim(), systemRole: canSetRole ? peranBaru : "EMPLOYEE" },
                      "Akun dibuat.",
                    )
                  }
                >
                  Buat akun
                </ActionButton>
              </>
            )}
          </div>
        )}
        {a?.exists && (
          <div className="flex flex-col gap-3">
            <TextBlock>
              <TextBlock as="span" className="font-medium">{a.login}</TextBlock>{" "}
              {a.is_active ? (
                <Pill tone="success">Aktif</Pill>
              ) : (
                <Pill>Nonaktif</Pill>
              )}
            </TextBlock>
            <TextBlock className="text-mist">
              Terakhir masuk:{" "}
              {a.last_login_at
                ? formatDateTime(a.last_login_at)
                : "belum pernah"}
            </TextBlock>
            {terkunci && a.locked_until ? (
              <TextBlock className="text-danger" data-testid="account-locked">
                <Pill tone="danger">Terkunci</Pill> {a.failed_logins} kali gagal login dalam 15 menit — bisa
                masuk lagi pukul {formatDateTime(a.locked_until)}.
              </TextBlock>
            ) : (a.failed_logins ?? 0) > 0 ? (
              <TextBlock className="text-warning" data-testid="account-failed">
                <Pill tone="warning">Gagal login</Pill> {a.failed_logins} kali dalam 15 menit terakhir (terkunci
                setelah 5 kali).
              </TextBlock>
            ) : (
              <TextBlock className="text-mist">
                <Pill tone="success">Tidak terkunci</Pill>
              </TextBlock>
            )}
            {(terkunci || (a.failed_logins ?? 0) > 0) && (
              <ActionButton
                variant="outline"
                className="self-start"
                disabled={action.isPending}
                onClick={() => run({ kind: "unlock" }, "Kunci akun dibuka. Karyawan bisa mencoba masuk lagi.")}
              >
                Buka kunci akun
              </ActionButton>
            )}
            {canSetRole && roleAkun && (
              <div className="flex flex-wrap items-end gap-2">
                <div className="min-w-48">
                  <RoleSelectField
                    label="Peran"
                    value={peranDipilih ?? roleAkun}
                    options={FIELD_ROLE_LABEL}
                    onChange={(v) => setPeranAkun(v as FieldRole)}
                  />
                </div>
                <ActionButton
                  variant="outline"
                  disabled={action.isPending || (peranDipilih ?? roleAkun) === roleAkun}
                  onClick={() =>
                    run({ kind: "role", systemRole: peranDipilih ?? roleAkun }, "Peran akun diperbarui.").then(() =>
                      setPeranAkun(null),
                    )
                  }
                >
                  Simpan peran
                </ActionButton>
              </div>
            )}
            {a.system_role && !roleAkun && (
              <TextBlock className="text-mist">Peran kantor: {a.system_role} (diatur di menu peran).</TextBlock>
            )}
            <div className="flex flex-wrap gap-2">
              <ActionButton
                variant="outline"
                disabled={action.isPending}
                onClick={() =>
                  run(
                    { kind: "reset" },
                    "Sandi direset; semua sesi akun ini dikeluarkan.",
                  )
                }
              >
                Reset sandi
              </ActionButton>
              {a.is_active ? (
                <ActionButton
                  variant="outline"
                  disabled={action.isPending}
                  onClick={() =>
                    run(
                      { kind: "deactivate" },
                      "Akun dinonaktifkan; sesi aktif dikeluarkan.",
                    )
                  }
                >
                  Nonaktifkan akun
                </ActionButton>
              ) : (
                employee.offboarding_status !== "offboarded" && (
                  <ActionButton
                    variant="outline"
                    disabled={action.isPending}
                    onClick={() =>
                      run({ kind: "activate" }, "Akun diaktifkan kembali.")
                    }
                  >
                    Aktifkan akun
                  </ActionButton>
                )
              )}
            </div>
            <div className="border-t border-line pt-4">
              <AccountLoginEditForm employeeId={employee.employee_id} login={a.login ?? ""} />
            </div>
            <div className="border-t border-line pt-4">
              <AccountDevicesAdmin employeeId={employee.employee_id} />
            </div>
            {canDelete && (
              <div className="mt-2 flex flex-col gap-2 rounded-control border border-danger bg-danger-soft p-3">
                <TextBlock className="font-semibold text-danger">Zona berbahaya</TextBlock>
                <TextBlock className="text-xs">
                  Hapus akun hanya bila karyawan tidak boleh masuk lagi. Ini tidak bisa dibatalkan; data karyawan
                  (profil, absensi, dokumen) tetap ada dan karyawan bisa dibuatkan akun baru nanti.
                </TextBlock>
                <DeleteConfirmButton
                  label="Hapus akun login"
                  title="Hapus akun login?"
                  description={`Akun login ${a.login} dihapus permanen dan semua perangkatnya dikeluarkan. Karyawan tidak bisa masuk sampai dibuatkan akun baru. Profil dan data karyawan tetap ada.`}
                  successText="Akun login dihapus."
                  onDelete={() => deleteAccount.mutateAsync()}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
