import { Button } from "../atoms/Button";

/**
 * Navigasi halaman untuk daftar bernomor halaman (Direktori, Audit log, …).
 *
 *   <ListPagination total={120} noun="karyawan" page={page} shownPage={data.page} lastPage={6} onPageChange={setPage} />
 */
export function ListPagination({ total, noun, page, shownPage, lastPage, onPageChange }: {
  total: number;
  /** Kata benda jumlah, mis. "karyawan", "catatan". */
  noun: string;
  /** Halaman yang dipilih (state Page). */
  page: number;
  /** Halaman milik data yang sedang tampil. */
  shownPage: number;
  lastPage: number;
  onPageChange: (page: number) => void;
}) {
  return (
        <nav aria-label="Halaman" className="mt-4 flex items-center justify-between text-sm">
          <span className="text-mist">
            {total} {noun} · halaman {shownPage} dari {lastPage}
          </span>
          <span className="flex gap-2">
            <Button variant="outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
              Sebelumnya
            </Button>
            <Button variant="outline" disabled={page >= lastPage} onClick={() => onPageChange(page + 1)}>
              Berikutnya
            </Button>
          </span>
        </nav>
  );
}
