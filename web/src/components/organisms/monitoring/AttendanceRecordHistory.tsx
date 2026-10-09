import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate, formatDateTime, formatTime } from "@/lib/format";
import type { AttendanceRecap } from "@/services/monitoringService";

/** Jam keluar; bila pulang tercatat di hari lain (absen yang baru disetujui belakangan) tampilkan tanggalnya. */
function checkOutLabel(workDate: string, checkOut: string | null | undefined): string {
  if (!checkOut) return "belum keluar";
  const outDay = new Date(checkOut).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" }); // YYYY-MM-DD
  const sameDay = outDay === workDate.slice(0, 10);
  return sameDay ? formatTime(checkOut) : formatDateTime(checkOut);
}

/** Riwayat jam masuk & keluar per absen (kartu di ponsel, tabel di desktop), termasuk kategori dalam/luar kota. */
export function AttendanceRecordHistory({ records }: { records: AttendanceRecap["records"] }) {
  return (
        <section aria-label="Riwayat absensi" className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">Riwayat absensi</h2>
          <ul className="grid gap-3 md:hidden">
            {records.map((r) => (
              <li key={r.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
                <div className="mb-1 flex items-start justify-between gap-2">
                  <p className="font-medium">{r.full_name}</p>
                  <StatusBadge status={r.status} />
                </div>
                <p className="text-sm text-mist">
                  {formatDate(r.work_date)} · {r.site_label}
                </p>
                <p className="mt-1 text-sm">
                  Masuk {formatTime(r.check_in_at)} · Keluar {checkOutLabel(r.work_date, r.check_out_at)}
                </p>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto rounded-panel border border-line bg-surface shadow-card md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-mist">
                <tr>
                  <th className="px-4 py-3 font-medium">Tanggal</th>
                  <th className="px-4 py-3 font-medium">Karyawan</th>
                  <th className="px-4 py-3 font-medium">Lokasi</th>
                  <th className="px-4 py-3 font-medium">Jam masuk</th>
                  <th className="px-4 py-3 font-medium">Jam keluar</th>
                  <th className="px-4 py-3 font-medium">Kategori</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="h-11 border-b border-line last:border-0">
                    <td className="px-4 py-2">{formatDate(r.work_date)}</td>
                    <td className="px-4 py-2 font-medium">{r.full_name}</td>
                    <td className="px-4 py-2">{r.site_label}</td>
                    <td className="px-4 py-2">
                      {formatTime(r.check_in_at)}
                      {r.is_late ? " · terlambat" : ""}
                    </td>
                    <td className="px-4 py-2">
                      {checkOutLabel(r.work_date, r.check_out_at)}
                      {r.is_early_leave ? " · pulang cepat" : ""}
                    </td>
                    <td className="px-4 py-2">{r.city_category === "LUAR_KOTA" ? "Luar kota" : "Dalam kota"}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
  );
}
