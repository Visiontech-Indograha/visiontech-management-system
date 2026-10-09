import type { UseQueryResult } from "@tanstack/react-query";
import { Button } from "@/components/atoms/Button";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { Asset } from "@/services/assetService";

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
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {assets.data?.map((a) => (
            <li key={a.id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold tracking-wide text-mist">{a.kind === "VEHICLE" ? "KENDARAAN" : "PERALATAN"}</span>
                <StatusBadge status={a.status} />
              </div>
              <h2 className="font-medium">{a.name}</h2>
              <dl className="text-sm text-mist">
                <div>Kode: {a.code}</div>
                <div>Kondisi: {a.condition}</div>
                {a.vehicle_type && <div>Jenis: {a.vehicle_type}</div>}
                {a.plan_number && <div>Dipakai: rencana kerja {a.plan_number}</div>}
                {a.pending_return_id && (
                  <div className="mt-1 text-warning">
                    Pengembalian diajukan {a.return_requested_by_name ?? "ketua tim"} · kondisi {a.return_condition}
                    {a.return_note ? ` — ${a.return_note}` : ""}
                  </div>
                )}
              </dl>
              <div className="mt-auto flex flex-col gap-2 md:flex-row md:flex-wrap">
                {canReserve && a.status === "AVAILABLE" && <Button onClick={() => onOpen({ kind: "reserve", asset: a })}>Alokasikan</Button>}
                {canReserve && a.status === "RESERVED" && (
                  <Button variant="outline" onClick={() => onOpen({ kind: "release", asset: a })}>
                    Lepas reservasi
                  </Button>
                )}
                {isBorrowingLeader(a) && a.allocation_id && !a.pending_return_id && ["IN_USE", "RESERVED"].includes(a.status) && (
                  <Button variant="outline" onClick={() => onOpen({ kind: "return", asset: a })}>
                    Ajukan pengembalian
                  </Button>
                )}
                {canManage && a.status === "RETURN_PENDING" && a.pending_return_id && (
                  <Button onClick={() => onOpen({ kind: "verify", asset: a })}>Periksa pengembalian</Button>
                )}
                <Button variant="ghost" onClick={() => onOpen({ kind: "history", asset: a })}>
                  Riwayat
                </Button>
                {a.kind === "VEHICLE" && a.status === "RESERVED" && (
                  <Button variant="outline" onClick={() => onOpen({ kind: "check", asset: a })}>
                    Periksa Kendaraan
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </QueryState>
  );
}
