import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { useListControls } from "@/hooks/useListControls";
import { pagedView, usePagedList, type ListControls } from "@/hooks/usePagedList";
import { formatDate } from "@/lib/format";
import { inspectionStatusLabel, inspectionStatusTone, INSPECTION_STATUS_LABEL, PERIOD_LABEL, periodLabel } from "@/lib/inspectionLabels";
import { useVehicles } from "@/services/assetService";
import { INSPECTION_KEY, INSPECTION_LIST_URL, INSPECTION_MINE_URL, type Inspection } from "@/services/inspectionService";

function InspectionFilters({ controls, mine, from, to }: { controls: ListControls; mine: boolean; from: string; to: string }) {
  const vehicles = useVehicles();
  const periods = Object.keys(PERIOD_LABEL);
  const statuses = Object.keys(INSPECTION_STATUS_LABEL);
  return (
    <ListToolbar value={controls.input} onChange={controls.setInput} placeholder="Cari plat, nama kendaraan, atau pemeriksa" active={controls.active} onReset={controls.reset}>
        <SelectField label="Kendaraan" value={controls.filter("vehicle")} onChange={(e) => controls.setFilter("vehicle", e.target.value)}>
          <ControlOption value="">Semua kendaraan</ControlOption>
          {(vehicles.data ?? []).map((v) => <ControlOption key={v.vehicle_id} value={v.vehicle_id}>{v.number_plate} - {v.name}</ControlOption>)}
        </SelectField>
        {!mine && (
          <>
            <SelectField label="Jenis pemeriksaan" value={controls.filter("period", periods)} onChange={(e) => controls.setFilter("period", e.target.value)}>
              <ControlOption value="">Semua jenis</ControlOption>
              {Object.entries(PERIOD_LABEL).map(([k, l]) => <ControlOption key={k} value={k}>{l}</ControlOption>)}
            </SelectField>
            <SelectField label="Status" value={controls.filter("status", statuses)} onChange={(e) => controls.setFilter("status", e.target.value)}>
              <ControlOption value="">Semua status</ControlOption>
              {Object.entries(INSPECTION_STATUS_LABEL).map(([k, l]) => <ControlOption key={k} value={k}>{l}</ControlOption>)}
            </SelectField>
          </>
        )}
        <TextField label="Dari tanggal" type="date" value={from} onChange={(e) => controls.setFilter("from", e.target.value)} />
        <TextField label="Sampai tanggal" type="date" value={to} onChange={(e) => controls.setFilter("to", e.target.value)} />
    </ListToolbar>
  );
}

function useInspectionPage(controls: ListControls, mine: boolean) {
  const from = controls.filter("from");
  const to = controls.filter("to");
  const invalidRange = Boolean(from && to && from > to);
  const range = invalidRange ? {} : { from_date: from || undefined, to_date: to || undefined };
  const own = { vehicle_id: controls.filter("vehicle") || undefined, ...range };
  const extra = mine ? own : { ...own, period_type: controls.filter("period", Object.keys(PERIOD_LABEL)) || undefined, status: controls.filter("status", Object.keys(INSPECTION_STATUS_LABEL)) || undefined };
  const query = usePagedList<Inspection>([...INSPECTION_KEY, mine ? "mine" : "all"], mine ? INSPECTION_MINE_URL : INSPECTION_LIST_URL, controls, extra);
  return { from, to, invalidRange, query };
}

/** Daftar inspeksi kendaraan (semua, atau milik saya) dengan filter, cari awalan, dan halaman. */
export function VehicleInspectionList({ mine, onOpen, onCreate, canCreate }: {
  mine: boolean;
  onOpen: (id: string) => void;
  onCreate: () => void;
  canCreate: boolean;
}) {
  const controls = useListControls({ prefix: mine ? "m" : "" });
  const { from, to, invalidRange, query } = useInspectionPage(controls, mine);
  const view = pagedView(query, controls);
  return (
    <div>
      <InspectionFilters controls={controls} mine={mine} from={from} to={to} />
      {invalidRange && <TextBlock role="alert" className="mb-3 text-sm text-danger">Tanggal awal tidak boleh setelah tanggal akhir.</TextBlock>}
      <QueryState
        query={query}
        errorText="Daftar inspeksi belum bisa dimuat. Periksa sambungan lalu coba lagi."
        empty={view.rows.length === 0}
        emptyText={controls.active ? "Tidak ada inspeksi yang cocok. Ubah atau atur ulang pencarian." : mine ? "Anda belum mengirim inspeksi kendaraan." : "Belum ada inspeksi kendaraan."}
        emptyAction={canCreate ? <ActionButton onClick={onCreate}>Buat inspeksi</ActionButton> : undefined}
      >
        <div className="overflow-x-auto rounded-panel border border-line bg-surface">
          <TableBlock className="w-full text-left text-sm">
            <TableBlockHead className="border-b border-line text-xs text-mist">
              <TableBlockRow>
                <TableBlockHeaderCell className="p-3">Kendaraan</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3">Jenis dan tanggal</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3">Pemeriksa</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3">Status</TableBlockHeaderCell>
                <TableBlockHeaderCell className="p-3 text-right">Aksi</TableBlockHeaderCell>
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {view.rows.map((r) => (
                <TableBlockRow key={r.inspection_id} className="border-b border-line">
                  <TableBlockCell className="p-3">
                    <TextBlock className="font-medium text-ink">{r.number_plate ?? "-"}</TextBlock>
                    <TextBlock className="text-xs text-mist">{r.vehicle_name ?? "-"}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="p-3">
                    <TextBlock>{periodLabel(r.period_type)}</TextBlock>
                    <TextBlock className="text-xs text-mist">{formatDate(r.inspection_date)}</TextBlock>
                  </TableBlockCell>
                  <TableBlockCell className="p-3">{r.inspector_name ?? "-"}</TableBlockCell>
                  <TableBlockCell className="p-3"><Pill tone={inspectionStatusTone(r.status)}>{inspectionStatusLabel(r.status)}</Pill></TableBlockCell>
                  <TableBlockCell className="p-3 text-right">
                    <ActionButton variant="outline" size="sm" onClick={() => onOpen(r.inspection_id)} aria-label={`Lihat inspeksi ${r.number_plate ?? ""}`}>Lihat</ActionButton>
                  </TableBlockCell>
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        </div>
        <ListPagination total={view.total} noun="inspeksi" page={view.page} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={controls.setPage} />
      </QueryState>
    </div>
  );
}
