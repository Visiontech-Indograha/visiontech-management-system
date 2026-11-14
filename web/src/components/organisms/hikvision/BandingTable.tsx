import { Pill } from "@/components/molecules/Pill";
import { Notice, NoticeDescription } from "@/components/molecules/Notice";
import { QueryState } from "@/components/molecules/QueryState";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListPagination } from "@/components/organisms/ListPagination";
import { STATUS_LABEL, STATUS_TONE, selisihLabel } from "@/lib/hikvisionBanding";
import { formatDate, formatTime } from "@/lib/format";
import type { BandingBaris, BandingBayangan } from "@/services/hikvisionService";

interface QueryLike {
  isPending: boolean;
  isError: boolean;
  refetch: () => unknown;
  data?: BandingBayangan;
}

/** Tabel pembanding mesin vs aplikasi: memuat, galat, kosong, sebagian (terpotong / tak terpetakan), berhasil. */
export function BandingTable({ query, rows, total, page, shownPage, lastPage, onPageChange, filtered }: {
  query: QueryLike;
  rows: BandingBaris[];
  total: number;
  page: number;
  shownPage: number;
  lastPage: number;
  onPageChange: (p: number) => void;
  filtered: boolean;
}) {
  const data = query.data;
  return (
    <QueryState
      query={query}
      errorText="Perbandingan belum bisa dimuat. Periksa sambungan lalu coba lagi."
      empty={total === 0}
      emptyText={filtered ? "Tidak ada data yang cocok. Ubah atau atur ulang pencarian." : "Belum ada catatan dari mesin pada tanggal ini."}
    >
      {data && data.tak_terpetakan > 0 && (
        <Notice className="mb-3">
          <NoticeDescription>{`${data.tak_terpetakan} catatan mesin belum dicocokkan ke karyawan, jadi tidak ikut dibandingkan.`}</NoticeDescription>
        </Notice>
      )}
      {data?.terpotong && (
        <Notice className="mb-3">
          <NoticeDescription>Data terlalu banyak, sebagian belum tampil. Persempit tanggal untuk melihat semuanya.</NoticeDescription>
        </Notice>
      )}
      <div className="overflow-x-auto rounded-panel border border-line bg-surface">
        <TableBlock className="w-full text-left text-sm">
          <TableBlockHead className="border-b border-line text-xs text-mist">
            <TableBlockRow>
              <TableBlockHeaderCell className="p-3">Karyawan</TableBlockHeaderCell>
              <TableBlockHeaderCell className="p-3">Tanggal</TableBlockHeaderCell>
              <TableBlockHeaderCell className="p-3">Di mesin</TableBlockHeaderCell>
              <TableBlockHeaderCell className="p-3">Di aplikasi</TableBlockHeaderCell>
              <TableBlockHeaderCell className="p-3">Selisih</TableBlockHeaderCell>
              <TableBlockHeaderCell className="p-3">Status</TableBlockHeaderCell>
            </TableBlockRow>
          </TableBlockHead>
          <TableBlockBody>
            {rows.map((r) => {
              const st = r.status;
              return (
                <TableBlockRow key={`${r.employee_id}-${r.tgl}`} className="border-b border-line">
                  <TableBlockCell className="p-3 font-medium text-ink">{r.employee_name}</TableBlockCell>
                  <TableBlockCell className="p-3">{formatDate(r.tgl)}</TableBlockCell>
                  <TableBlockCell className="p-3">{r.pertama && r.terakhir ? `${formatTime(r.pertama)} - ${formatTime(r.terakhir)} (${r.jumlah}x)` : "Tidak ada di mesin"}</TableBlockCell>
                  <TableBlockCell className="p-3">
                    {r.clock_in_at || r.clock_out_at ? `${formatTime(r.clock_in_at)} - ${formatTime(r.clock_out_at)}` : "Belum absen"}
                  </TableBlockCell>
                  <TableBlockCell className="p-3 text-mist">
                    <TextBlock>{`Masuk: ${selisihLabel(r.selisih_masuk_menit)}`}</TextBlock>
                    <TextBlock>{`Pulang: ${selisihLabel(r.selisih_pulang_menit)}`}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="p-3"><Pill tone={STATUS_TONE[st]}>{STATUS_LABEL[st]}</Pill></TableBlockCell>
                </TableBlockRow>
              );
            })}
          </TableBlockBody>
        </TableBlock>
      </div>
      <ListPagination total={total} noun="data" page={page} shownPage={shownPage} lastPage={lastPage} onPageChange={onPageChange} />
    </QueryState>
  );
}
