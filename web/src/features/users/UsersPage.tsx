import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { EMPLOYMENT_LABEL, ROLE_LABEL, type UserOut } from "@/lib/types";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { useUsers } from "./api";
import {
  CreateUserDialog,
  DeactivateDialog,
  EditUserDialog,
  ResetPasswordDialog,
  TemporaryPasswordDialog,
} from "./UserDialogs";
import { useActivate } from "./useActivate";

const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";

export function UsersPage() {
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebouncedValue(q, 300);
  const users = useUsers({ q: search, role, is_active: active, page });

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<UserOut | null>(null);
  const [resetting, setResetting] = useState<UserOut | null>(null);
  const [deactivating, setDeactivating] = useState<UserOut | null>(null);
  const [temp, setTemp] = useState<{ username: string; password: string } | null>(null);
  const activate = useActivate();

  const data = users.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader title="Pengguna" action={<Button onClick={() => setCreating(true)}>Tambah user</Button>} />

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          aria-label="Cari nama atau username"
          placeholder="Cari nama atau username..."
          className={`${inputCls} w-64`}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
        <select
          aria-label="Filter role"
          className={inputCls}
          value={role}
          onChange={(e) => {
            setRole(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Semua role</option>
          {["super_admin", "admin", "team_leader", "finance", "hes", "user"].map((v) => (
            <option key={v} value={v}>
              {ROLE_LABEL[v]}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter status akun"
          className={inputCls}
          value={active}
          onChange={(e) => {
            setActive(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Semua status</option>
          <option value="true">Aktif</option>
          <option value="false">Nonaktif</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 border-b border-line bg-surface text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Nama</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Status kerja</th>
              <th className="px-4 py-3 font-medium">Akun</th>
              <th className="px-4 py-3 text-right font-medium">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {users.isPending &&
              Array.from({ length: 5 }, (_, i) => (
                <tr key={i} className="border-b border-line last:border-0" aria-hidden>
                  <td colSpan={5} className="h-11 px-4">
                    <div className="h-3 w-1/2 animate-pulse rounded-tag bg-hover" />
                  </td>
                </tr>
              ))}
            {users.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-danger">
                  Daftar pengguna tidak dapat dimuat.{" "}
                  <button className="font-semibold underline" onClick={() => void users.refetch()}>
                    Coba lagi
                  </button>
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Tidak ada pengguna yang cocok.
                </td>
              </tr>
            )}
            {data?.items.map((u) => (
              <tr key={u.id} className="h-11 border-b border-line last:border-0 hover:bg-hover">
                <td className="px-4 py-2">
                  <div className="font-medium">{u.full_name}</div>
                  <div className="text-xs text-mist">{u.username}</div>
                </td>
                <td className="px-4 py-2">{ROLE_LABEL[u.user_type ?? u.role]}</td>
                <td className="px-4 py-2">{u.employment_type ? EMPLOYMENT_LABEL[u.employment_type] : "-"}</td>
                <td className="px-4 py-2">
                  {u.is_active ? <Badge tone="success">Aktif</Badge> : <Badge>Nonaktif</Badge>}
                </td>
                <td className="whitespace-nowrap px-4 py-2 text-right">
                  <Button variant="ghost" className="h-8 px-2" onClick={() => setEditing(u)}>
                    Ubah
                  </Button>
                  <Button variant="ghost" className="h-8 px-2" onClick={() => setResetting(u)}>
                    Reset password
                  </Button>
                  {u.is_active ? (
                    <Button variant="ghost" className="h-8 px-2 text-danger" onClick={() => setDeactivating(u)}>
                      Nonaktifkan
                    </Button>
                  ) : (
                    <Button variant="ghost" className="h-8 px-2" onClick={() => void activate(u)}>
                      Aktifkan
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > data.page_size && (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {data.total} pengguna · halaman {data.page} dari {lastPage}
          </span>
          <span className="flex gap-2">
            <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Sebelumnya
            </Button>
            <Button variant="outline" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
              Berikutnya
            </Button>
          </span>
        </nav>
      )}

      <CreateUserDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(username, password) => setTemp({ username, password })}
      />
      <EditUserDialog key={editing?.id} user={editing} onClose={() => setEditing(null)} />
      <ResetPasswordDialog
        user={resetting}
        onClose={() => setResetting(null)}
        onDone={(username, password) => setTemp({ username, password })}
      />
      <DeactivateDialog key={deactivating?.id} user={deactivating} onClose={() => setDeactivating(null)} />
      <TemporaryPasswordDialog
        username={temp?.username ?? ""}
        password={temp?.password ?? null}
        onClose={() => setTemp(null)}
      />
    </>
  );
}
