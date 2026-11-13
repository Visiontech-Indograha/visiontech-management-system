import { ListBlock } from "@/components/molecules/ListBlock";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListPagination } from "@/components/organisms/ListPagination";
import { useListControls } from "@/hooks/useListControls";
import { pagedView, usePagedList } from "@/hooks/usePagedList";
import { DOC_KEY, type VehicleDocument } from "@/services/vehicleDocumentService";
import { DocumentRow } from "./DocumentRow";

/** "Dokumen saya" karyawan (SIM dan sejenisnya) dari /vehicle-documents/mine. */
export function MyVehicleDocsPanel() {
  const controls = useListControls();
  const query = usePagedList<VehicleDocument>([...DOC_KEY, "mine"], "/vehicle-documents/mine", controls);
  const view = pagedView(query, controls);
  return (
    <QueryState query={query} errorText="Dokumen Anda tidak dapat dimuat." empty={query.data?.total === 0} emptyText="Belum ada dokumen atas nama Anda.">
      <TextBlock className="mb-3 text-sm text-mist">Bila dokumen sudah diperpanjang, minta petugas HSE mencatatnya.</TextBlock>
      <ListBlock className="divide-y divide-line rounded-panel border border-line bg-surface shadow-card">
        {view.rows.map((d) => <DocumentRow key={d.vehicle_document_id} doc={d} />)}
      </ListBlock>
      {view.total > 0 && <ListPagination total={view.total} noun="dokumen" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
    </QueryState>
  );
}
