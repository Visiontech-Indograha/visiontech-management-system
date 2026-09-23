import { Link } from "react-router-dom";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatDate } from "@/lib/format";
import { EMPLOYMENT_LABEL, ROLE_LABEL } from "@/lib/types";
import { useIncomplete } from "./api";

/** Worklist HES: karyawan aktif dengan berkas wajib kurang (FR-DOC-05). */
export function IncompletePage() {
  const list = useIncomplete();
  return (
    <>
      <PageHeader title="Perlu dilengkapi" />
      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Karyawan</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Berkas yang kurang</th>
              <th className="px-4 py-3 font-medium">Kedaluwarsa terdekat</th>
              <th className="px-4 py-3 text-right font-medium">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {list.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-danger">
                  Daftar tidak dapat dimuat.
                </td>
              </tr>
            )}
            {list.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-mist">
                  Semua berkas wajib sudah lengkap.
                </td>
              </tr>
            )}
            {list.data?.map((r) => (
              <tr key={r.user_id} className="border-b border-line last:border-0 hover:bg-hover">
                <td className="px-4 py-3 font-medium">{r.full_name}</td>
                <td className="px-4 py-3">
                  {ROLE_LABEL[r.user_type ?? r.role]}
                  {r.employment_type && <span className="text-mist"> · {EMPLOYMENT_LABEL[r.employment_type]}</span>}
                </td>
                <td className="px-4 py-3">
                  <span className="mr-2 text-mist">{r.missing_count}</span>
                  {r.missing.map((m) => m.name).join(", ")}
                </td>
                <td className="px-4 py-3">{r.nearest_expiry ? formatDate(r.nearest_expiry) : "-"}</td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/directory/${r.user_id}`} className="font-semibold text-lens hover:underline">
                    Unggah berkas
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
