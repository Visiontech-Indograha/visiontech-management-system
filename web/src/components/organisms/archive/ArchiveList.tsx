import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { QueryState } from "@/components/molecules/QueryState";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ArchiveRestoreDialog } from "@/components/organisms/archive/ArchiveRestoreDialog";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useListControls } from "@/hooks/useListControls";
import { pagedView, usePagedList } from "@/hooks/usePagedList";
import { formatDate } from "@/lib/format";
import { ARCHIVE_KEY, archiveUrl, type ArchiveItem } from "@/services/archiveService";

/** Daftar item terhapus satu modul: cari awalan nama, halaman, dan tombol Pulihkan dengan konfirmasi. */
export function ArchiveList({ slug, label, codeLabel }: { slug: string; label: string; codeLabel: string }) {
  const controls = useListControls({});
  const query = usePagedList<ArchiveItem>([...ARCHIVE_KEY, slug], archiveUrl(slug), controls);
  const view = pagedView(query, controls);
  const [target, setTarget] = useState<ArchiveItem | null>(null);
  return (
    <div>
      <ListToolbar value={controls.input} onChange={controls.setInput} placeholder="Cari dari awal nama" active={controls.active} onReset={controls.reset} />
      <QueryState
        query={query}
        errorText="Arsip belum bisa dimuat. Periksa sambungan lalu coba lagi."
        empty={view.rows.length === 0}
        emptyText={controls.active ? "Tidak ada data yang cocok. Ubah atau atur ulang pencarian." : `Tidak ada ${label.toLowerCase()} yang dihapus.`}
      >
        <div className="overflow-x-auto rounded-panel border border-line bg-surface">
          <TableBlock className="w-full text-left text-sm">
            <TableBlockHead className="border-b border-line text-xs text-mist">
              <TableBlockRow>
                <TableBlockHeaderCell className="p-3">Nama</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3">{codeLabel}</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3">Dihapus pada</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3 text-right">Aksi</TableBlockHeaderCell>
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {view.rows.map((r) => (
                <TableBlockRow key={r.id} className="border-b border-line">
                  <TableBlockCell className="p-3 font-medium text-ink">{r.name}</TableBlockCell>
                  <TableBlockCell className="p-3">{r.code ?? "-"}</TableBlockCell>
                  <TableBlockCell className="p-3 text-mist">{r.deleted_at ? formatDate(r.deleted_at) : "-"}</TableBlockCell>
                  <TableBlockCell className="p-3 text-right">
                    <ActionButton variant="outline" size="sm" onClick={() => setTarget(r)} aria-label={`Pulihkan ${r.name}`}>Pulihkan</ActionButton>
                  </TableBlockCell>
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        </div>
        <ListPagination total={view.total} noun="data" page={view.page} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={controls.setPage} />
      </QueryState>
      {target && <ArchiveRestoreDialog slug={slug} moduleLabel={label} item={target} onClose={() => setTarget(null)} />}
      <TextBlock className="sr-only" aria-live="polite">{view.total} data di arsip {label.toLowerCase()}</TextBlock>
    </div>
  );
}
