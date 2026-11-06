import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { KeysetMore } from "@/hooks/useKeysetList";

/** Tombol "Muat lebih banyak" untuk daftar keyset (tanpa jumlah total) + pesan bila daftar dimulai ulang. */
export function LoadMoreBar({ more }: { more: KeysetMore }) {
  return (
    <div className="mt-4 space-y-2">
      {more.notice && (
        <TextBlock role="status" className="rounded-control border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
          {more.notice}
        </TextBlock>
      )}
      {more.hasMore && (
        <ActionButton variant="outline" disabled={more.loading} onClick={more.onLoadMore}>
          {more.loading ? "Memuat…" : "Muat lebih banyak"}
        </ActionButton>
      )}
    </div>
  );
}
