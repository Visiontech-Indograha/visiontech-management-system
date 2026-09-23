import { Badge } from "@/components/ui/Badge";
import { formatDate, formatDateTime } from "@/lib/format";
import { useMyAttendance, usePolicy } from "./api";

/** Ringkasan absen di Beranda. Absen web mati secara default (BR-08): arahkan ke aplikasi Android. */
export function HomeAttendance() {
  const policy = usePolicy();
  const history = useMyAttendance();
  const p = policy.data;
  const today = history.data?.find((a) => a.attendance_date === p?.attendance_date);
  const cutoff = p?.cutoff_time.slice(0, 5).replace(":", ".");

  return (
    <section aria-label="Absensi" className="mt-6 max-w-2xl">
      <h2 className="mb-2 text-base font-semibold">Absensi</h2>
      <p className="mb-3 text-sm text-mist">
        {p && !p.allow_web
          ? "Absen luar kota dilakukan lewat aplikasi Android."
          : "Absen dilakukan dari perangkat dengan lokasi yang dapat diverifikasi."}
        {cutoff && ` Batas absen pukul ${cutoff} WIB.`}
      </p>
      <p className="mb-4 text-sm" role="status">
        {today ? (
          <>
            <Badge tone="success">Sudah absen</Badge>{" "}
            {today.is_manual ? "(koreksi manual)" : formatDateTime(today.checked_in_at)}
          </>
        ) : p ? (
          <Badge tone={p.window_open ? "info" : "warning"}>
            {p.window_open ? "Belum absen hari ini" : "Belum absen · jendela absen sudah ditutup"}
          </Badge>
        ) : null}
      </p>
      {history.data && history.data.length > 0 && (
        <div className="overflow-x-auto rounded-panel border border-line bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-mist">
              <tr>
                <th className="px-4 py-2 font-medium">Tanggal</th>
                <th className="px-4 py-2 font-medium">Jam</th>
                <th className="px-4 py-2 font-medium">Keterangan</th>
              </tr>
            </thead>
            <tbody>
              {history.data.slice(0, 7).map((a) => (
                <tr key={a.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-2">{formatDate(a.attendance_date)}</td>
                  <td className="px-4 py-2">{a.is_manual ? "-" : formatDateTime(a.checked_in_at).slice(-9)}</td>
                  <td className="px-4 py-2">
                    {a.is_manual ? <Badge tone="info">Manual</Badge> : a.risk_flags.length > 0 ? <Badge tone="warning">Perlu ditinjau</Badge> : "Normal"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
