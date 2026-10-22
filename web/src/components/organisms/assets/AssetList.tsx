/**
 * web/src/components/organisms/assets/AssetList.tsx
 * Inventaris aset V2: tab Kendaraan / Alat / Sedang dipinjam. Pemegang & masa STNK/KIR dari API;
 * tindakan (serahkan, terima kembali, status, berkas) hanya untuk pengelola aset.
 */

import { useState } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry, ListPair } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { useLoans, useTools, useVehicles, type AssetKind, type Loan, type Tool, type Vehicle } from "@/services/assetService";

/** Dialog yang dibuka dari kartu aset. */
export type AssetAction =
  | { kind: "lend"; asset: AssetKind; id: string; name: string }
  | { kind: "status"; asset: AssetKind; id: string; name: string; status: string }
  | { kind: "files"; vehicle: Vehicle }
  | { kind: "return"; loan: Loan };

type Tab = "VEHICLE" | "TOOL" | "LOANS";
const VEHICLE_TYPE: Record<string, string> = { Motorcycle: "Motor", Car: "Mobil", Truck: "Truk / pick-up" };
const OWNERSHIP: Record<string, string> = { PERSONAL_LOAN: "Alat pribadi", SHARED_TOOL: "Alat bersama" };

function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
}

function PaperPill({ label, date, required }: { label: string; date?: string | null; required: boolean }) {
  if (!date) return required ? <Pill tone="danger">{`${label} belum ada`}</Pill> : null;
  if (date < today()) return <Pill tone="danger">{`${label} kedaluwarsa`}</Pill>;
  return <Pill tone="neutral">{`${label} s.d. ${formatDate(date)}`}</Pill>;
}

function Holder({ name }: { name?: string | null }) {
  return name ? <ListPair>Dipegang: <TextBlock as="span" className="text-ink">{name}</TextBlock></ListPair> : null;
}

function TabButton({ active, onClick, label, count }: { active: boolean; onClick: () => void; label: string; count?: number }) {
  return (
    <ActionButton variant={active ? "default" : "outline"} size="sm" onClick={onClick} className="h-9 text-xs">
      {count !== undefined ? `${label} (${count})` : label}
    </ActionButton>
  );
}

export function AssetList({ canManage, onOpen }: { canManage: boolean; onOpen: (action: AssetAction) => void }) {
  const [tab, setTab] = useState<Tab>("VEHICLE");
  const vehicles = useVehicles();
  const tools = useTools();
  const loans = useLoans(true);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 border-b border-line pb-3">
        <TabButton active={tab === "VEHICLE"} onClick={() => setTab("VEHICLE")} label="Kendaraan" count={vehicles.data?.length} />
        <TabButton active={tab === "TOOL"} onClick={() => setTab("TOOL")} label="Alat" count={tools.data?.length} />
        <TabButton active={tab === "LOANS"} onClick={() => setTab("LOANS")} label="Sedang dipinjam" count={loans.data?.length} />
      </div>

      {tab === "VEHICLE" && (
        <QueryState query={vehicles} errorText="Daftar kendaraan tidak dapat dimuat." empty={vehicles.data?.length === 0} emptyText="Belum ada kendaraan.">
          <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {vehicles.data?.map((v) => (
              <ListEntry key={v.vehicle_id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface p-4 shadow-card">
                <div className="flex items-center justify-between gap-2">
                  <TextBlock as="span" className="font-mono text-sm">{v.number_plate}</TextBlock>
                  <StatusBadge status={v.status} />
                </div>
                <TextBlock as="h2" className="text-base font-medium">{v.name}</TextBlock>
                <ListBlock as="dl" className="space-y-1 text-xs text-mist">
                  <ListPair>{VEHICLE_TYPE[v.vehicle_type]} · {v.division_name} · {v.office_name}</ListPair>
                  <Holder name={v.holder_name} />
                </ListBlock>
                <div className="flex flex-wrap gap-1">
                  <PaperPill label="STNK" date={v.stnk_expired_at} required />
                  <PaperPill label="KIR" date={v.kir_expired_at} required={v.vehicle_type === "Truck"} />
                </div>
                <VehicleActions vehicle={v} canManage={canManage} onOpen={onOpen} />
              </ListEntry>
            ))}
          </ListBlock>
        </QueryState>
      )}

      {tab === "TOOL" && (
        <QueryState query={tools} errorText="Daftar alat tidak dapat dimuat." empty={tools.data?.length === 0} emptyText="Belum ada alat.">
          <ListBlock className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {tools.data?.map((t) => (
              <ListEntry key={t.tool_id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface p-4 shadow-card">
                <div className="flex items-center justify-between gap-2">
                  <TextBlock as="span" className="font-mono text-sm">{t.tool_code}</TextBlock>
                  <StatusBadge status={t.status} />
                </div>
                <TextBlock as="h2" className="text-base font-medium">{t.name}</TextBlock>
                <ListBlock as="dl" className="space-y-1 text-xs text-mist">
                  <ListPair>{OWNERSHIP[t.ownership_type]} · {t.division_name ?? "Semua divisi"} · {t.office_name}</ListPair>
                  <Holder name={t.holder_name} />
                </ListBlock>
                <ToolActions tool={t} canManage={canManage} onOpen={onOpen} />
              </ListEntry>
            ))}
          </ListBlock>
        </QueryState>
      )}

      {tab === "LOANS" && (
        <QueryState query={loans} errorText="Daftar peminjaman tidak dapat dimuat." empty={loans.data?.length === 0} emptyText="Tidak ada aset yang sedang dipinjam.">
          <ListBlock className="divide-y divide-line rounded-panel border border-line bg-surface shadow-card">
            {loans.data?.map((l) => (
              <ListEntry key={l.assignment_id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                <div className="min-w-0 flex-1">
                  <TextBlock className="font-medium">{l.asset_name} · {l.asset_code}</TextBlock>
                  <TextBlock className="text-xs text-mist">
                    {l.employee_name} · sejak {formatDate(l.loaned_at)}
                    {l.work_date ? ` · jadwal ${formatDate(l.work_date)}` : ""}
                  </TextBlock>
                </div>
                <StatusBadge status={l.assignment_status} />
                {canManage && (
                  <ActionButton size="sm" variant="outline" onClick={() => onOpen({ kind: "return", loan: l })}>
                    Terima kembali
                  </ActionButton>
                )}
              </ListEntry>
            ))}
          </ListBlock>
        </QueryState>
      )}
    </div>
  );
}

function VehicleActions({ vehicle: v, canManage, onOpen }: { vehicle: Vehicle; canManage: boolean; onOpen: (a: AssetAction) => void }) {
  return (
    <div className="mt-auto flex flex-wrap gap-2 border-t border-line/60 pt-2">
      {canManage && v.status === "ready" && (
        <ActionButton size="sm" onClick={() => onOpen({ kind: "lend", asset: "VEHICLE", id: v.vehicle_id, name: v.name })}>
          Serahkan
        </ActionButton>
      )}
      <ActionButton size="sm" variant="outline" onClick={() => onOpen({ kind: "files", vehicle: v })}>
        Berkas
      </ActionButton>
      {canManage && !v.assignment_id && (
        <ActionButton size="sm" variant="ghost" onClick={() => onOpen({ kind: "status", asset: "VEHICLE", id: v.vehicle_id, name: v.name, status: v.status })}>
          Status
        </ActionButton>
      )}
    </div>
  );
}

function ToolActions({ tool: t, canManage, onOpen }: { tool: Tool; canManage: boolean; onOpen: (a: AssetAction) => void }) {
  if (!canManage) return null;
  return (
    <div className="mt-auto flex flex-wrap gap-2 border-t border-line/60 pt-2">
      {t.status === "ready" && (
        <ActionButton size="sm" onClick={() => onOpen({ kind: "lend", asset: "TOOL", id: t.tool_id, name: t.name })}>
          Serahkan
        </ActionButton>
      )}
      {!t.assignment_id && (
        <ActionButton size="sm" variant="ghost" onClick={() => onOpen({ kind: "status", asset: "TOOL", id: t.tool_id, name: t.name, status: t.status })}>
          Status
        </ActionButton>
      )}
    </div>
  );
}
