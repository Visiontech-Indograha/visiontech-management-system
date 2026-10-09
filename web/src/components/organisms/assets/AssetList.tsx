import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { Asset } from "@/services/assetService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry, ListPair } from "@/components/molecules/ListBlock";

/** Dialog aset yang dibuka dari kartu. */
export type AssetAction = { kind: "reserve" | "release" | "check" | "return" | "verify" | "history"; asset: Asset };

/** Kartu kendaraan & alat dengan tombol sesuai status dan kedudukan; keadaan memuat/galat/kosong. */
export function AssetList({ assets, canManage, canReserve, isBorrowingLeader, onOpen }: {
  assets: UseQueryResult<Asset[]>;
  canManage: boolean;
  canReserve: boolean;
  /** Ketua rencana kerja peminjam (bukan petugas aset) — boleh mengajukan pengembalian. */
  isBorrowingLeader: (asset: Asset) => boolean;
  onOpen: (action: AssetAction) => void;
}) {
  return (
      <QueryState query={assets} errorText="Daftar aset tidak dapat dimuat." empty={assets.data?.length === 0} emptyText="Belum ada kendaraan atau alat.">
        <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {assets.data?.map((a) => (
            <ListEntry key={a.id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
              <div className="flex items-center justify-between gap-2">
                <TextBlock as="span" className="text-xs font-semibold tracking-wide text-mist">{a.kind === "VEHICLE" ? "KENDARAAN" : "PERALATAN"}</TextBlock>
                <StatusBadge status={a.status} />
              </div>
              <TextBlock as="h2" className="font-medium">{a.name}</TextBlock>
              <ListBlock as="dl" className="text-sm text-mist">
                <ListPair>Kode: {a.code}</ListPair>
                <ListPair>Kondisi: {a.condition}</ListPair>
                {a.vehicle_type && <ListPair>Jenis: {a.vehicle_type}</ListPair>}
                {a.plan_number && <ListPair>Dipakai: rencana kerja {a.plan_number}</ListPair>}
                {a.pending_return_id && (
                  <ListPair className="mt-1 text-warning">
                    Pengembalian diajukan {a.return_requested_by_name ?? "ketua tim"} · kondisi {a.return_condition}
                    {a.return_note ? ` — ${a.return_note}` : ""}
                  </ListPair>
                )}
              </ListBlock>
              <div className="mt-auto flex flex-col gap-2 md:flex-row md:flex-wrap">
                {canReserve && a.status === "AVAILABLE" && <ActionButton onClick={() => onOpen({ kind: "reserve", asset: a })}>Alokasikan</ActionButton>}
                {canReserve && a.status === "RESERVED" && (
                  <ActionButton variant="outline" onClick={() => onOpen({ kind: "release", asset: a })}>
                    Lepas reservasi
                  </ActionButton>
                )}
                {isBorrowingLeader(a) && a.allocation_id && !a.pending_return_id && ["IN_USE", "RESERVED"].includes(a.status) && (
                  <ActionButton variant="outline" onClick={() => onOpen({ kind: "return", asset: a })}>
                    Ajukan pengembalian
                  </ActionButton>
                )}
                {canManage && a.status === "RETURN_PENDING" && a.pending_return_id && (
                  <ActionButton onClick={() => onOpen({ kind: "verify", asset: a })}>Periksa pengembalian</ActionButton>
                )}
                <ActionButton variant="ghost" onClick={() => onOpen({ kind: "history", asset: a })}>
                  Riwayat
                </ActionButton>
                {a.kind === "VEHICLE" && a.status === "RESERVED" && (
                  <ActionButton variant="outline" onClick={() => onOpen({ kind: "check", asset: a })}>
                    Periksa Kendaraan
                  </ActionButton>
                )}
              </div>
            </ListEntry>
          ))}
        </ListBlock>
      </QueryState>
  );
}
