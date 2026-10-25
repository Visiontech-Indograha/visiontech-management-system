import { useState } from "react";
import { toast } from "sonner";
import { TextField } from "@/components/molecules/Field";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAccount, useAccountAction, useDeleteAccount, type Employee } from "@/services/employeeService";
import { DeleteConfirmButton } from "@/components/organisms/DeleteConfirmButton";
import { Pill } from "@/components/molecules/Pill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { SectionTitle } from "@/components/molecules/SectionTitle";

/**
 * M1-01 · HR/admin mengelola akun login karyawan: buat akun, reset password, nonaktifkan/aktifkan.
 * Password sementara ditampilkan SEKALI di sini — sampaikan ke karyawan, lalu minta diganti di
 * "Akun & keamanan" setelah masuk.
 */
export function AccountCard({ employee }: { employee: Employee }) {
  const account = useAccount(employee.employee_id);
  const action = useAccountAction(employee.employee_id);
  const deleteAccount = useDeleteAccount(employee.employee_id);
  const [login, setLogin] = useState(employee.email ?? "");
  const [issued, setIssued] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
            <TextBlock as="span">Password sementara (hanya ditampilkan sekali): </TextBlock>
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
                <ActionButton
                  className="self-start"
                  disabled={action.isPending || !login.trim()}
                  onClick={() =>
                    run({ kind: "create", login: login.trim() }, "Akun dibuat.")
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
            {a.locked_until && new Date(a.locked_until) > new Date() ? (
              <TextBlock className="text-danger" data-testid="account-locked">
                <Pill tone="danger">Terkunci</Pill> {a.failed_logins} kali gagal login dalam 15 menit — bisa
                masuk lagi pukul {formatDateTime(a.locked_until)}.
              </TextBlock>
            ) : (a.failed_logins ?? 0) > 0 ? (
              <TextBlock className="text-warning" data-testid="account-failed">
                <Pill tone="warning">Gagal login</Pill> {a.failed_logins} kali dalam 15 menit terakhir (terkunci
                setelah 5 kali).
              </TextBlock>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <ActionButton
                variant="outline"
                disabled={action.isPending}
                onClick={() =>
                  run(
                    { kind: "reset" },
                    "Password direset; semua sesi akun ini dikeluarkan.",
                  )
                }
              >
                Reset password
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
              <DeleteConfirmButton
                label="Hapus akun"
                title="Hapus akun login?"
                description={`Akun login ${a.login} dihapus permanen; data karyawannya tetap ada.`}
                successText="Akun login dihapus."
                onDelete={() => deleteAccount.mutateAsync()}
              />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
