import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock } from "@/components/molecules/ListBlock";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useListControls } from "@/hooks/useListControls";
import { pagedView, usePagedList } from "@/hooks/usePagedList";
import { DOC_KEY, EXPIRING_DAYS, type VehicleDocument } from "@/services/vehicleDocumentService";
import { DocumentRow } from "./DocumentRow";

/** Dokumen kendaraan yang akan atau sudah jatuh tempo (urut jatuh tempo dari API) untuk HSE/OM/SA. */
export function ExpiringDocsPanel({ canManage, onRenew, filter }: {
  canManage: boolean;
  onRenew: (doc: VehicleDocument) => void;
  /** Filter tambahan ke API (mis. jenis/kantor) setelah parameternya ada di openapi; belum dipakai. */
  filter?: Record<string, string | undefined>;
}) {
  const controls = useListControls();
  const query = usePagedList<VehicleDocument>(DOC_KEY, "/vehicle-documents/expiring", controls, { days: EXPIRING_DAYS, ...filter });
  const view = pagedView(query, controls);
  return (
    <QueryState query={query} errorText="Daftar dokumen tidak dapat dimuat." empty={query.data?.total === 0 && !view.active} emptyText={`Tidak ada dokumen yang jatuh tempo dalam ${EXPIRING_DAYS} hari ke depan.`}>
      <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari plat nomor, kendaraan, atau jenis dokumen..." active={view.active} onReset={view.reset} />
      {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
      <ListBlock className="divide-y divide-line rounded-panel border border-line bg-surface shadow-card">
        {view.rows.map((d) => (
          <DocumentRow
            key={d.vehicle_document_id}
            doc={d}
            action={canManage && <ActionButton size="sm" variant="outline" onClick={() => onRenew(d)}>Perbarui dokumen</ActionButton>}
          />
        ))}
      </ListBlock>
      {view.total > 0 && <ListPagination total={view.total} noun="dokumen" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
    </QueryState>
  );
}
