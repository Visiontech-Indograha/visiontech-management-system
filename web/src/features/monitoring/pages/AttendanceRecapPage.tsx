import { useState } from "react";
import { QueryState } from "@/components/molecules/QueryState";
import { TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/organisms/PageHeader";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate, formatDateTime, formatTime } from "@/lib/format";
import { useAttendanceRecap } from "../monitoringService";

type Count = "days_present" | "auto_valid" | "needs_review" | "approved" | "rejected";
const COLS: [string, Count][] = [
  ["Hadir", "days_present"],
  ["Valid otomatis", "auto_valid"],
  ["Perlu review", "needs_review"],
  ["Disetujui", "approved"],
  ["Ditolak", "rejected"],
];

/** Rekap absensi per karyawan per bulan (GET /recaps/attendance). Cakupan data ditentukan API (R-33:
 * Finance & OPS semua, PM bawahannya, lainnya milik sendiri) + riwayat jam masuk & keluar. */
export function AttendanceRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useAttendanceRecap(month);
  const rows = recap.data?.employees ?? [];
  const records = recap.data?.records ?? [];

  return (
    <>
      <PageHeader title="Rekap absensi" />
      <div className="md:max-w-xs">
        <TextField
          label="Bulan"
          type="month"
          value={month || recap.data?.month || ""}
          onChange={(e) => setMonth(e.target.value)}
          hint="Kosong = bulan berjalan."
        />
      </div>
      <QueryState
        query={recap}
        errorText="Rekap absensi tidak dapat dimuat."
        empty={rows.length === 0}
        emptyText="Belum ada catatan kehadiran pada bulan ini."
      >
        <ul className="grid gap-3 md:hidden">
          {rows.map((r) => (
            <li key={r.employee_id} className="rounded-panel border border-line bg-surface shadow-card p-4">
              <p className="mb-2 font-medium">{r.full_name}</p>
              <dl className="grid grid-cols-2 gap-1 text-sm">
                {COLS.map(([label, k]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt className="text-mist">{label}</dt>
                    <dd>{r[k]}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
        <div className="hidden overflow-x-auto rounded-panel border border-line bg-surface shadow-card md:block">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-mist">
              <tr>
                <th className="px-4 py-3 font-medium">Karyawan</th>
                {COLS.map(([label]) => (
                  <th key={label} className="px-4 py-3 text-right font-medium">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.employee_id} className="h-11 border-b border-line last:border-0">
                  <td className="px-4 py-2 font-medium">{r.full_name}</td>
                  {COLS.map(([, k]) => (
                    <td key={k} className="px-4 py-2 text-right">
                      {r[k]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryState>

      {records.length > 0 && (
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
      )}
    </>
  );
}

/** Jam keluar; bila pulang tercatat di hari lain (absen yang baru disetujui belakangan) tampilkan tanggalnya. */
function checkOutLabel(workDate: string, checkOut: string | null | undefined): string {
  if (!checkOut) return "belum keluar";
  const outDay = new Date(checkOut).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" }); // YYYY-MM-DD
  const sameDay = outDay === workDate.slice(0, 10);
  return sameDay ? formatTime(checkOut) : formatDateTime(checkOut);
}
