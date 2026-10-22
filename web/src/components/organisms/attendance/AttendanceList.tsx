import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate, formatDateTime } from "@/lib/format";
import type { Attendance, AttendanceList as AttendanceListData } from "@/services/attendanceService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Kartu absensi (jarak, wajah, penjelasan, status) + tombol Tinjau/Beri penjelasan + navigasi halaman. */
export function AttendanceList({ list, page, meEmployeeId, onPageChange, onOpen }: {
  list: UseQueryResult<AttendanceListData>;
  page: number;
  meEmployeeId: string | null | undefined;
  onPageChange: (page: number) => void;
  onOpen: (open: { kind: "review" | "explain"; item: Attendance }) => void;
}) {
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  return (
      <QueryState query={list} errorText="Absensi tidak dapat dimuat." empty={data?.items.length === 0} emptyText="Tidak ada catatan kehadiran yang cocok.">
        <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data?.items.map((a) => (
            <ListEntry key={a.id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <TextBlock className="font-medium">{a.employee_name ?? "-"}</TextBlock>
                  <TextBlock className="text-sm text-mist">
                    {formatDate(a.work_date)} · {a.site_label}
                  </TextBlock>
                </div>
                <StatusBadge status={a.status} />
              </div>
              <ListBlock as="dl" className="text-sm">
                <div>
                  <TextBlock as="dt" className="inline text-mist">Masuk / keluar: </TextBlock>
                  <TextBlock as="dd" className="inline">
                    {formatDateTime(a.check_in_at)} / {a.check_out_at ? formatDateTime(a.check_out_at) : "belum keluar"}
                  </TextBlock>
                </div>
                <div>
                  <TextBlock as="dt" className="inline text-mist">Jarak: </TextBlock>
                  <TextBlock as="dd" className="inline">
                    {Math.round(a.distance_m)} m{a.is_late ? " · terlambat" : ""}
                    {a.is_early_leave ? " · pulang cepat" : ""}
                    {a.offline ? " · absen offline" : ""}
                  </TextBlock>
                </div>
                <div>
                  <TextBlock as="dt" className="inline text-mist">Uang Makan: </TextBlock>
                  <TextBlock as="dd" className="inline font-medium text-emerald-400">
                    {a.meal_allowance_amount != null
                      ? `Rp ${Math.round(a.meal_allowance_amount).toLocaleString("id-ID")}`
                      : "-"}
                    {a.city_category === "LUAR_KOTA" ? " (Luar Kota > 15 km)" : " (Dalam Kota)"}
                  </TextBlock>
                </div>
                {a.check_out_distance_m != null && (
                  <div>
                    <TextBlock as="dt" className="inline text-mist">Jarak pulang: </TextBlock>
                    <TextBlock as="dd" className="inline">
                      {Math.round(a.check_out_distance_m)} m{a.check_out_outside ? " · Pulang di luar radius" : ""}
                    </TextBlock>
                  </div>
                )}
                {(a.face_result || a.check_out_face_result) && (
                  <div>
                    <TextBlock as="dt" className="inline text-mist">Wajah: </TextBlock>
                    <TextBlock as="dd" className="inline">
                      {a.face_result
                        ? `Masuk: ${a.face_result}${a.face_similarity !== null && a.face_similarity !== undefined ? ` (${Math.round(a.face_similarity * 100)}%)` : ""}`
                        : ""}
                      {a.face_result && a.check_out_face_result ? " · " : ""}
                      {a.check_out_face_result
                        ? `Pulang: ${a.check_out_face_result}${a.check_out_face_similarity !== null && a.check_out_face_similarity !== undefined ? ` (${Math.round(a.check_out_face_similarity * 100)}%)` : ""}`
                        : ""}
                    </TextBlock>
                  </div>
                )}
                {a.explanation && (
                  <div>
                    <TextBlock as="dt" className="inline text-mist">Penjelasan: </TextBlock>
                    <TextBlock as="dd" className="inline">{a.explanation}</TextBlock>
                  </div>
                )}
                <div className="text-mist">
                  {a.status === "AUTO_VALID"
                    ? "Tidak perlu ditinjau · jarak dalam radius"
                    : a.status === "NEEDS_REVIEW"
                      ? "Menunggu pemeriksaan"
                      : `Ditinjau ${a.reviewed_at ? formatDateTime(a.reviewed_at) : ""}`}
                </div>
              </ListBlock>
              {a.status === "NEEDS_REVIEW" && (
                <div className="mt-auto flex flex-col gap-2 md:flex-row">
                  {a.can_review ? (
                    <ActionButton onClick={() => onOpen({ kind: "review", item: a })}>Tinjau</ActionButton>
                  ) : a.employee_id === meEmployeeId ? (
                    <ActionButton variant="outline" onClick={() => onOpen({ kind: "explain", item: a })}>
                      {a.explanation ? "Ubah penjelasan" : "Beri penjelasan"}
                    </ActionButton>
                  ) : null}
                </div>
              )}
            </ListEntry>
          ))}
        </ListBlock>
        {data && data.total > data.size && (
          <nav aria-label="Halaman" className="mt-4 flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
            <TextBlock as="span" className="text-mist">
              {data.total} catatan · halaman {data.page} dari {lastPage}
            </TextBlock>
            <TextBlock as="span" className="flex gap-2">
              <ActionButton variant="outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
                Sebelumnya
              </ActionButton>
              <ActionButton variant="outline" disabled={page >= lastPage} onClick={() => onPageChange(page + 1)}>
                Berikutnya
              </ActionButton>
            </TextBlock>
          </nav>
        )}
      </QueryState>
  );
}
