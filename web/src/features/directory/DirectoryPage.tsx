import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { PageHeader } from "@/components/molecules/PageHeader";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { useSession } from "@/app/session";
import { PAGE_SIZE, useEmployees } from "./api";
import { CreateEmployeeDialog } from "./Lifecycle";

const inputCls = "h-10 rounded-control border border-line bg-surface px-3 text-sm";

export function DirectoryPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const canManage = !!useSession().me?.permissions.includes("manage:users");
  const search = useDebouncedValue(q, 300);
  const list = useEmployees({ q: search, status, page });
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };
  const cols = 4;

  return (
    <>
      <PageHeader
        title="Direktori"
        action={canManage && <Button onClick={() => setCreating(true)}>Tambah karyawan</Button>}
      />
      {creating && <CreateEmployeeDialog onClose={() => setCreating(false)} />}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          aria-label="Cari nama atau no. karyawan"
          placeholder="Cari nama atau no. karyawan..."
          className={`${inputCls} w-full md:w-64`}
          value={q}
          onChange={(e) => reset(setQ)(e.target.value)}
        />
        <select aria-label="Filter akun" className={inputCls} value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
          <option value="active">Aktif</option>
          <option value="inactive">Nonaktif</option>
          <option value="all">Semua</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 border-b border-line bg-surface text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Nama</th>
              <th className="px-4 py-3 font-medium">Jabatan</th>
              <th className="px-4 py-3 font-medium">Bergabung</th>
              <th className="px-4 py-3 font-medium">Akun</th>
            </tr>
          </thead>
          <tbody>
            {list.isPending && (
              <tr aria-hidden>
                <td colSpan={cols} className="h-11 px-4">
                  <div className="h-3 w-1/2 animate-pulse rounded-tag bg-hover" />
                </td>
              </tr>
            )}
            {list.isError && (
              <tr>
                <td colSpan={cols} className="px-4 py-6 text-center text-danger">
                  Direktori tidak dapat dimuat.{" "}
                  <Button variant="outline" size="sm" onClick={() => list.refetch()}>
                    Coba lagi
                  </Button>
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={cols} className="px-4 py-6 text-center text-mist">
                  Tidak ada karyawan yang cocok.
                </td>
              </tr>
            )}
            {data?.items.map((e) => (
              <tr key={e.id} className="h-11 border-b border-line last:border-0 hover:bg-hover">
                <td className="px-4 py-2">
                  <Link to={`/directory/${e.id}`} state={{ employee: e }} className="font-medium text-lens hover:underline">
                    {e.full_name}
                  </Link>
                  <div className="text-xs text-mist">{e.employee_no}</div>
                </td>
                <td className="px-4 py-2">{e.position}</td>
                <td className="px-4 py-2">{formatDate(e.join_date)}</td>
                <td className="px-4 py-2">{e.is_active ? <Badge tone="success">Aktif</Badge> : <Badge>Nonaktif</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > PAGE_SIZE && (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {data.total} karyawan · halaman {data.page} dari {lastPage}
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
    </>
  );
}
