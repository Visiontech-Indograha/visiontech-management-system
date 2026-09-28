import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAccount, useAccountAction, type Employee } from "./api";

/**
 * M1-01 · HR/admin mengelola akun login karyawan: buat akun, reset password, nonaktifkan/aktifkan.
 * Password sementara ditampilkan SEKALI di sini — sampaikan ke karyawan, lalu minta diganti di
 * "Akun & keamanan" setelah masuk.
 */
export function AccountCard({ employee }: { employee: Employee }) {
  const account = useAccount(employee.id);
  const action = useAccountAction(employee.id);
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
      <h2 className="mb-3 text-base font-semibold">Akun login</h2>
      <div className="rounded-panel border border-line bg-surface px-5 py-4 text-sm shadow-card">
        {account.isPending && <Skeleton className="h-4 w-2/3" />}
        {account.isError && (
          <p className="text-danger">Status akun tidak dapat dimuat.</p>
        )}
        {error && (
          <p
            role="alert"
            className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-danger"
          >
            {error}
          </p>
        )}
        {issued && (
          <div
            role="status"
            className="mb-3 rounded-control bg-brand-50 px-3 py-2"
          >
            Password sementara (hanya ditampilkan sekali):{" "}
            <code className="select-all font-mono font-semibold">{issued}</code>
            <p className="mt-1 text-caption text-mist">
              Sampaikan langsung ke karyawan; minta diganti setelah masuk.
            </p>
          </div>
        )}
        {a && !a.exists && (
          <div className="flex flex-col gap-3">
            <p className="text-mist">Karyawan ini belum punya akun login.</p>
            {employee.is_active && (
              <>
                <TextField
                  label="Email login"
                  type="email"
                  value={login}
                  onChange={(e) => setLogin(e.target.value)}
                />
                <Button
                  className="self-start"
                  disabled={action.isPending || !login.trim()}
                  onClick={() =>
                    run({ kind: "create", login: login.trim() }, "Akun dibuat.")
                  }
                >
                  Buat akun
                </Button>
              </>
            )}
          </div>
        )}
        {a?.exists && (
          <div className="flex flex-col gap-3">
            <p>
              <span className="font-medium">{a.login}</span>{" "}
              {a.is_active ? (
                <Badge tone="success">Aktif</Badge>
              ) : (
                <Badge>Nonaktif</Badge>
              )}
            </p>
            <p className="text-mist">
              Terakhir masuk:{" "}
              {a.last_login_at
                ? formatDateTime(a.last_login_at)
                : "belum pernah"}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
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
              </Button>
              {a.is_active ? (
                <Button
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
                </Button>
              ) : (
                employee.is_active && (
                  <Button
                    variant="outline"
                    disabled={action.isPending}
                    onClick={() =>
                      run({ kind: "activate" }, "Akun diaktifkan kembali.")
                    }
                  >
                    Aktifkan akun
                  </Button>
                )
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
