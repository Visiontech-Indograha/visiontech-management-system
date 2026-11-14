import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useListControls } from "@/hooks/useListControls";
import { pagedView, usePagedList } from "@/hooks/usePagedList";
import { BORROWERS_KEY, type Borrower } from "@/services/assetService";
import { BorrowerFormDialog } from "./BorrowerFormDialog";

/** Kelola penerima luar perusahaan: cari (awalan nama), tambah, ubah. Izin manage:assets. */
export function BorrowersDialog({ onClose }: { onClose: () => void }) {
  const controls = useListControls({ prefix: "pnr_" });
  const query = usePagedList<Borrower>(BORROWERS_KEY, "/assets/external-borrowers", controls);
  const view = pagedView(query, controls);
  const [form, setForm] = useState<{ borrower?: Borrower } | null>(null);
  return (
    <VmsDialog open title="Penerima dari luar perusahaan" size="md" onClose={onClose}
      footer={<ActionButton onClick={() => setForm({})}>Tambah penerima</ActionButton>}>
      <QueryState query={query} errorText="Daftar penerima tidak dapat dimuat." empty={query.data?.total === 0 && !view.active}
        emptyText="Belum ada penerima. Tambahkan dulu sebelum menyerahkan aset ke pihak luar.">
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari nama penerima..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="p-4 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="divide-y divide-line rounded-panel border border-line">
          {view.rows.map((b) => (
            <ListEntry key={b.borrower_id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
              <div className="min-w-0 flex-1">
                <TextBlock className="truncate font-medium">{b.nama}</TextBlock>
                <TextBlock className="truncate text-xs text-mist">
                  {[b.instansi, b.kontak, b.office_name].filter(Boolean).join(" · ")}
                </TextBlock>
              </div>
              {b.has_open_loan && <Pill tone="neutral">Sedang meminjam</Pill>}
              <ActionButton size="sm" variant="outline" aria-label={`Ubah ${b.nama}`} onClick={() => setForm({ borrower: b })}>Ubah</ActionButton>
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="penerima" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
      </QueryState>
      {form && <BorrowerFormDialog borrower={form.borrower} onClose={() => setForm(null)} />}
    </VmsDialog>
  );
}
