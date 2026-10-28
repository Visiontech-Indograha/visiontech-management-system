import { useSearchParams } from "react-router-dom";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate, formatDateTime, formatTime } from "@/lib/format";
import type { AttendanceRecap } from "@/services/monitoringService";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";

/** Jam keluar; bila pulang tercatat di hari lain (absen yang baru disetujui belakangan) tampilkan tanggalnya. */
function checkOutLabel(workDate: string, checkOut: string | null | undefined): string {
  if (!checkOut) return "belum keluar";
  const outDay = new Date(checkOut).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" }); // YYYY-MM-DD
  const sameDay = Boolean(workDate && outDay === workDate.slice(0, 10));
  return sameDay ? formatTime(checkOut) : formatDateTime(checkOut);
}

/** Riwayat jam masuk & keluar per absen (kartu di ponsel, tabel di desktop), termasuk kategori dalam/luar kota. */
export function AttendanceRecordHistory({ records: all }: { records: AttendanceRecap["records"] }) {
  // Pencarian nama pada rekap (?abs_q=) berlaku juga untuk riwayat di bawahnya.
  const [params] = useSearchParams();
  const needle = (params.get("abs_q") ?? "").trim().toLowerCase();
  const records = needle ? all.filter((r) => r.full_name.toLowerCase().includes(needle)) : all;
  if (records.length === 0) return null;
  return (
        <section aria-label="Riwayat absensi" className="mt-8">
          <TextBlock as="h2" className="mb-3 text-lg font-semibold">Riwayat absensi</TextBlock>
          <ListBlock className="grid gap-3 md:hidden">
            {records.map((r) => (
              <ListEntry key={r.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
                <div className="mb-1 flex items-start justify-between gap-2">
                  <TextBlock className="font-medium">{r.full_name}</TextBlock>
                  <StatusBadge status={r.status} />
                </div>
                <TextBlock className="text-sm text-mist">
                  {formatDate(r.work_date)} · {r.site_label}
                </TextBlock>
                <TextBlock className="mt-1 text-sm">
                  Masuk {formatTime(r.check_in_at)} · Keluar {checkOutLabel(r.work_date, r.check_out_at)}
                </TextBlock>
              </ListEntry>
            ))}
          </ListBlock>
          <div className="hidden overflow-x-auto rounded-panel border border-line bg-surface shadow-card md:block">
            <TableBlock className="w-full text-left text-sm">
              <TableBlockHead className="border-b border-line text-mist">
                <TableBlockRow>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Tanggal</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Karyawan</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Lokasi</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Jam masuk</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Jam keluar</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Kategori</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="px-4 py-3 font-medium">Status</TableBlockHeaderCell>
                </TableBlockRow>
              </TableBlockHead>
              <TableBlockBody>
                {records.map((r) => (
                  <TableBlockRow key={r.id} className="h-11 border-b border-line last:border-0">
                    <TableBlockCell className="px-4 py-2">{formatDate(r.work_date)}</TableBlockCell>
                    <TableBlockCell className="px-4 py-2 font-medium">{r.full_name}</TableBlockCell>
                    <TableBlockCell className="px-4 py-2">{r.site_label}</TableBlockCell>
                    <TableBlockCell className="px-4 py-2">
                      {formatTime(r.check_in_at)}
                      {r.is_late ? " · terlambat" : ""}
                    </TableBlockCell>
                    <TableBlockCell className="px-4 py-2">
                      {checkOutLabel(r.work_date, r.check_out_at)}
                      {r.is_early_leave ? " · pulang cepat" : ""}
                    </TableBlockCell>
                    <TableBlockCell className="px-4 py-2">{r.city_category === "LUAR_KOTA" ? "Luar kota" : "Dalam kota"}</TableBlockCell>
                    <TableBlockCell className="px-4 py-2">
                      <StatusBadge status={r.status} />
                    </TableBlockCell>
                  </TableBlockRow>
                ))}
              </TableBlockBody>
            </TableBlock>
          </div>
        </section>
  );
}
