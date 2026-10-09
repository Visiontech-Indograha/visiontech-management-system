import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { formatDate } from "@/lib/format";
import type { EmployeeList } from "../employeeService";

/** Tabel karyawan dengan keadaan memuat, galat (+ coba lagi), kosong, dan berhasil. */
export function EmployeeTable({ list }: { list: UseQueryResult<EmployeeList> }) {
  const data = list.data;
  const cols = 4;
  return (
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
  );
}
