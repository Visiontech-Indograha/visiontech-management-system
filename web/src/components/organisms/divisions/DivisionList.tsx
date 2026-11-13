import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextField } from "@/components/molecules/Field";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { QueryState } from "@/components/molecules/QueryState";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import type { DivisionRow, PositionRow } from "@/services/divisionAdminService";

const startsWith = (value: string | null | undefined, q: string) => (value ?? "").toLowerCase().startsWith(q);

/** Daftar divisi beserta jabatannya. Tombol kelola hanya tampil bila pengguna punya izin yang sesuai. */
export function DivisionList({
  divisions, positions, search, onSearch, canDivisions, canPositions,
  onAddDivision, onEditDivision, onRemoveDivision, onAddPosition, onEditPosition, onRemovePosition,
}: {
  divisions: UseQueryResult<DivisionRow[]>;
  positions: UseQueryResult<PositionRow[]>;
  search: string;
  onSearch: (value: string) => void;
  canDivisions: boolean;
  canPositions: boolean;
  onAddDivision: () => void;
  onEditDivision: (d: DivisionRow) => void;
  onRemoveDivision: (d: DivisionRow) => void;
  onAddPosition: (divisionId: string | null) => void;
  onEditPosition: (p: PositionRow) => void;
  onRemovePosition: (p: PositionRow) => void;
}) {
  const q = search.trim().toLowerCase();
  const byDivision = new Map<string, PositionRow[]>();
  for (const p of positions.data ?? []) {
    const key = p.division_id ?? "";
    byDivision.set(key, [...(byDivision.get(key) ?? []), p]);
  }
  const posMatch = (p: PositionRow) => startsWith(p.name, q) || startsWith(p.code, q);
  const rows = (divisions.data ?? []).filter(
    (d) => !q || startsWith(d.name, q) || startsWith(d.code, q) || (byDivision.get(d.id) ?? []).some(posMatch),
  );
  const shown = (d: DivisionRow) => {
    const all = byDivision.get(d.id) ?? [];
    return q && !startsWith(d.name, q) && !startsWith(d.code, q) ? all.filter(posMatch) : all;
  };
  const general = (byDivision.get("") ?? []).filter((p) => !q || posMatch(p));

  const positionRow = (p: PositionRow) => (
    <ListEntry key={p.position_id} className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-2">
      <div className="min-w-0">
        <TextBlock className="break-words text-sm font-medium">{`${p.name} (${p.code})`}</TextBlock>
        <TextBlock className="text-xs text-mist">{`Tingkat ${p.grade_level} · ${p.employee_count} karyawan`}</TextBlock>
      </div>
      {canPositions && (
        <div className="flex gap-2">
          <ActionButton size="sm" variant="outline" onClick={() => onEditPosition(p)}>Ubah</ActionButton>
          <ActionButton size="sm" variant="outline" onClick={() => onRemovePosition(p)}>Hapus</ActionButton>
        </div>
      )}
    </ListEntry>
  );

  return (
    <div className="space-y-4">
      <div className="w-full sm:w-72">
        <TextField label="Cari" placeholder="Awal nama atau kode divisi/jabatan" value={search} onChange={(e) => onSearch(e.target.value)} />
      </div>
      {divisions.isSuccess && positions.isError && (
        <RetryNotice message="Daftar jabatan belum bisa dimuat." onRetry={() => positions.refetch()} />
      )}
      <QueryState
        query={divisions}
        errorText="Daftar divisi belum bisa dimuat."
        empty={rows.length === 0 && general.length === 0}
        emptyText={q ? "Tidak ada divisi atau jabatan yang cocok." : "Belum ada divisi."}
        emptyAction={canDivisions && !q ? <ActionButton onClick={onAddDivision}>Tambah divisi</ActionButton> : undefined}
      >
        <ListBlock className="grid gap-3">
          {rows.map((d) => (
            <ListEntry key={d.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <TextBlock className="break-words font-semibold">{`${d.name} (${d.code})`}</TextBlock>
                  <TextBlock className="text-sm text-mist">{`OM: ${d.om_name ?? "belum dipilih"} · PM: ${d.pm_name ?? "belum dipilih"} · ${d.team_count} tim`}</TextBlock>
                </div>
                <div className="flex flex-wrap gap-2">
                  {canPositions && <ActionButton size="sm" variant="outline" onClick={() => onAddPosition(d.id)}>Tambah jabatan</ActionButton>}
                  {canDivisions && <ActionButton size="sm" variant="outline" onClick={() => onEditDivision(d)}>Ubah</ActionButton>}
                  {canDivisions && <ActionButton size="sm" variant="outline" onClick={() => onRemoveDivision(d)}>Hapus</ActionButton>}
                </div>
              </div>
              <ListBlock className="mt-3">
                {shown(d).length === 0 && <TextBlock className="text-sm text-mist">Belum ada jabatan di divisi ini.</TextBlock>}
                {shown(d).map(positionRow)}
              </ListBlock>
            </ListEntry>
          ))}
          {general.length > 0 && (
            <ListEntry className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <TextBlock className="font-semibold">Jabatan umum (tanpa divisi)</TextBlock>
                {canPositions && <ActionButton size="sm" variant="outline" onClick={() => onAddPosition(null)}>Tambah jabatan</ActionButton>}
              </div>
              <ListBlock className="mt-3">{general.map(positionRow)}</ListBlock>
            </ListEntry>
          )}
        </ListBlock>
      </QueryState>
    </div>
  );
}
