interface PaginationProps {
  skip: number;
  limit: number;
  /** Jumlah baris yang dikembalikan request terakhir — dipakai menebak apakah ada halaman berikutnya. */
  currentCount: number;
  onSkipChange: (skip: number) => void;
}

/**
 * Pager sederhana berbasis skip/limit (API tidak mengembalikan total count).
 * "Next" aktif bila jumlah baris yang diterima == limit (kemungkinan masih ada lagi).
 */
export const Pagination = ({ skip, limit, currentCount, onSkipChange }: PaginationProps) => {
  const page = Math.floor(skip / limit) + 1;
  const hasPrev = skip > 0;
  const hasNext = currentCount === limit;

  if (!hasPrev && !hasNext) return null;

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
      <div className="text-sm text-gray-500">Halaman {page}</div>
      <div className="flex space-x-2">
        <button
          type="button"
          disabled={!hasPrev}
          onClick={() => onSkipChange(Math.max(0, skip - limit))}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Sebelumnya
        </button>
        <button
          type="button"
          disabled={!hasNext}
          onClick={() => onSkipChange(skip + limit)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Berikutnya
        </button>
      </div>
    </div>
  );
};
