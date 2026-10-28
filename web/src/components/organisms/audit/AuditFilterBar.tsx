import { TextField } from "@/components/molecules/Field";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import type { ListControls } from "@/hooks/usePagedList";
import { AuditEntityFilter } from "./AuditEntityFilter";

/** Baris saringan audit log: cari (awalan aksi/tabel/pelaku), entitas, dan rentang tanggal; tersinkron ke URL. */
export function AuditFilterBar({ controls, entity, dateFrom, dateTo, invalidRange }: {
  controls: ListControls;
  entity: string;
  dateFrom: string;
  dateTo: string;
  invalidRange: boolean;
}) {
  return (
    <>
      <ListToolbar
        value={controls.input}
        onChange={controls.setInput}
        placeholder="Cari aksi, tabel, atau nama pelaku (awalan)..."
        active={controls.active}
        onReset={controls.reset}
      >
        <AuditEntityFilter entity={entity} onEntityChange={(v) => controls.setFilter("entity", v)} />
        <TextField label="Dari tanggal" type="date" value={dateFrom} onChange={(e) => controls.setFilter("from", e.target.value)} />
        <TextField label="Sampai tanggal" type="date" value={dateTo} onChange={(e) => controls.setFilter("to", e.target.value)} />
      </ListToolbar>
      {invalidRange && <TextBlock className="text-sm text-danger">Tanggal awal tidak boleh setelah tanggal akhir.</TextBlock>}
    </>
  );
}
