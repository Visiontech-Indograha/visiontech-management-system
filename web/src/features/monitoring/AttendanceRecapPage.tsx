import { useState } from "react";
import { QueryState } from "@/components/molecules/QueryState";
import { TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAttendanceRecap } from "./api";

type Count = "days_present" | "auto_valid" | "needs_review" | "approved" | "rejected";
const COLS: [string, Count][] = [
  ["Hadir", "days_present"],
  ["Valid otomatis", "auto_valid"],
  ["Perlu review", "needs_review"],
  ["Disetujui", "approved"],
  ["Ditolak", "rejected"],
];

/** Rekap absensi per karyawan per bulan (GET /recaps/attendance). Cakupan data ditentukan API. */
export function AttendanceRecapPage() {
  const [month, setMonth] = useState("");
  const recap = useAttendanceRecap(month);
  const rows = recap.data?.employees ?? [];

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
            <li key={r.employee_id} className="rounded-panel border border-line bg-surface p-4">
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
        <div className="hidden overflow-x-auto rounded-panel border border-line bg-surface md:block">
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
    </>
  );
}
