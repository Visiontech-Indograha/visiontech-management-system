/**
 * web/src/components/organisms/assets/AssetList.tsx
 * Komponen daftar kendaraan dan peralatan kerja dengan tab terpisah,
 * filter kepemilikan alat (Personal Loan vs Shared Tool), dan penanganan status alokasi.
 */

import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { Asset } from "@/services/assetService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry, ListPair } from "@/components/molecules/ListBlock";
import { Button } from "@/components/atoms/Button";
import {
  Car,
  HardHat,
  Truck,
  Wrench,
} from "lucide-react";

/** Dialog aset yang dibuka dari kartu. */
export type AssetAction = {
  kind: "reserve" | "release" | "check" | "return" | "verify" | "history";
  asset: Asset;
};

export function AssetList({
  assets,
  canManage,
  canReserve,
  isBorrowingLeader,
  onOpen,
}: {
  assets: UseQueryResult<Asset[]>;
  canManage: boolean;
  canReserve: boolean;
  isBorrowingLeader: (asset: Asset) => boolean;
  onOpen: (action: AssetAction) => void;
}) {
  const [activeTab, setActiveTab] = useState<"VEHICLE" | "TOOL">("VEHICLE");
  const [toolOwnershipFilter, setToolOwnershipFilter] = useState<"ALL" | "PERSONAL" | "SHARED">("ALL");

  const allAssets = assets.data ?? [];
  const vehicles = allAssets.filter((a) => a.kind === "VEHICLE");
  const tools = allAssets.filter((a) => a.kind === "TOOL");

  const filteredTools = tools.filter((t) => {
    if (toolOwnershipFilter === "ALL") return true;
    const lowerName = (t.name || "").toLowerCase();
    const isPersonal = lowerName.includes("baju") || lowerName.includes("sepatu") || lowerName.includes("laptop") || lowerName.includes("helm");
    if (toolOwnershipFilter === "PERSONAL") return isPersonal;
    if (toolOwnershipFilter === "SHARED") return !isPersonal;
    return true;
  });

  const displayedAssets = activeTab === "VEHICLE" ? vehicles : filteredTools;

  return (
    <div className="space-y-4">
      {/* Tab Navigasi Utama: Kendaraan vs Peralatan */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === "VEHICLE" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("VEHICLE")}
            className="text-xs h-9 gap-2"
          >
            <Truck className="w-4 h-4 text-sky-400" />
            <span>Armada Kendaraan</span>
            <span className="ml-1 text-[11px] px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-300">
              {vehicles.length}
            </span>
          </Button>

          <Button
            variant={activeTab === "TOOL" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("TOOL")}
            className="text-xs h-9 gap-2"
          >
            <Wrench className="w-4 h-4 text-amber-400" />
            <span>Peralatan Kerja</span>
            <span className="ml-1 text-[11px] px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-300">
              {tools.length}
            </span>
          </Button>
        </div>

        {/* Sub-filter untuk Tab Peralatan */}
        {activeTab === "TOOL" && (
          <div className="flex items-center gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => setToolOwnershipFilter("ALL")}
              className={`px-2.5 py-1 rounded-md border text-xs transition ${
                toolOwnershipFilter === "ALL"
                  ? "bg-amber-600 text-white border-amber-600 font-medium"
                  : "bg-surface text-mist border-line hover:text-foreground"
              }`}
            >
              Semua ({tools.length})
            </button>
            <button
              type="button"
              onClick={() => setToolOwnershipFilter("PERSONAL")}
              className={`px-2.5 py-1 rounded-md border text-xs flex items-center gap-1 transition ${
                toolOwnershipFilter === "PERSONAL"
                  ? "bg-amber-600 text-white border-amber-600 font-medium"
                  : "bg-surface text-mist border-line hover:text-foreground"
              }`}
            >
              <HardHat className="w-3 h-3" />
              Pinjaman Pribadi
            </button>
            <button
              type="button"
              onClick={() => setToolOwnershipFilter("SHARED")}
              className={`px-2.5 py-1 rounded-md border text-xs flex items-center gap-1 transition ${
                toolOwnershipFilter === "SHARED"
                  ? "bg-amber-600 text-white border-amber-600 font-medium"
                  : "bg-surface text-mist border-line hover:text-foreground"
              }`}
            >
              <Wrench className="w-3 h-3" />
              Peralatan Bersama
            </button>
          </div>
        )}
      </div>

      {/* Konten Daftar Aset */}
      <QueryState
        query={assets}
        errorText="Daftar aset tidak dapat dimuat."
        empty={displayedAssets.length === 0}
        emptyText={
          activeTab === "VEHICLE"
            ? "Belum ada kendaraan operasional yang terdaftar."
            : "Tidak ada peralatan kerja yang sesuai dengan filter."
        }
      >
        <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {displayedAssets.map((a) => {
            const isVehicle = a.kind === "VEHICLE";

            return (
              <ListEntry
                key={a.id}
                className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-mist">
                    {isVehicle ? (
                      <>
                        <Car className="w-3.5 h-3.5 text-sky-400" />
                        <span>KENDARAAN</span>
                      </>
                    ) : (
                      <>
                        <Wrench className="w-3.5 h-3.5 text-amber-400" />
                        <span>PERALATAN</span>
                      </>
                    )}
                  </div>
                  <StatusBadge status={a.status} />
                </div>

                <TextBlock as="h2" className="font-medium text-base text-white">
                  {a.name}
                </TextBlock>

                <ListBlock as="dl" className="text-xs text-mist space-y-1">
                  <ListPair>Kode / Plat: <span className="font-mono text-slate-200">{a.code}</span></ListPair>
                  <ListPair>Kondisi: <span className="text-slate-200">{a.condition}</span></ListPair>
                  {a.vehicle_type && <ListPair>Kategori: {a.vehicle_type}</ListPair>}
                  {a.plan_number && (
                    <ListPair className="text-sky-400 font-medium">
                      Alokasi: Rencana Kerja #{a.plan_number}
                    </ListPair>
                  )}
                  {a.pending_return_id && (
                    <ListPair className="mt-1 text-warning bg-amber-950/40 p-2 rounded border border-amber-800/40">
                      Pengembalian diajukan oleh {a.return_requested_by_name ?? "ketua tim"} · kondisi {a.return_condition}
                      {a.return_note ? ` — "${a.return_note}"` : ""}
                    </ListPair>
                  )}
                </ListBlock>

                <div className="mt-auto pt-2 border-t border-line/60 flex flex-wrap gap-2">
                  {canReserve && a.status === "AVAILABLE" && (
                    <ActionButton size="sm" onClick={() => onOpen({ kind: "reserve", asset: a })}>
                      Alokasikan
                    </ActionButton>
                  )}
                  {canReserve && a.status === "RESERVED" && (
                    <ActionButton
                      size="sm"
                      variant="outline"
                      onClick={() => onOpen({ kind: "release", asset: a })}
                    >
                      Lepas reservasi
                    </ActionButton>
                  )}
                  {isBorrowingLeader(a) &&
                    a.allocation_id &&
                    !a.pending_return_id &&
                    ["IN_USE", "RESERVED"].includes(a.status) && (
                      <ActionButton
                        size="sm"
                        variant="outline"
                        onClick={() => onOpen({ kind: "return", asset: a })}
                      >
                        Ajukan pengembalian
                      </ActionButton>
                    )}
                  {canManage && a.status === "RETURN_PENDING" && a.pending_return_id && (
                    <ActionButton
                      size="sm"
                      onClick={() => onOpen({ kind: "verify", asset: a })}
                    >
                      Periksa pengembalian
                    </ActionButton>
                  )}
                  <ActionButton
                    size="sm"
                    variant="ghost"
                    onClick={() => onOpen({ kind: "history", asset: a })}
                  >
                    Riwayat
                  </ActionButton>
                  {isVehicle && a.status === "RESERVED" && (
                    <ActionButton
                      size="sm"
                      variant="outline"
                      onClick={() => onOpen({ kind: "check", asset: a })}
                    >
                      Inspeksi Fisik
                    </ActionButton>
                  )}
                </div>
              </ListEntry>
            );
          })}
        </ListBlock>
      </QueryState>
    </div>
  );
}
