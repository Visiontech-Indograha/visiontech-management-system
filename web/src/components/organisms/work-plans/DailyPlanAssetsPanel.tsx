import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { statusLabel } from "@/lib/labels";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useAssetAvailability, useTools, useVehicles, type AssetKind } from "@/services/assetService";

type AssetRow = { kind: AssetKind; id: string; name: string; status: string };

/**
 * Aset bawaan tim (kendaraan & alat dengan tim pemakai = tim jadwal) beserta ketersediaannya pada tanggal jadwal.
 * Bentrok dengan tim lain ditandai dengan nama tim pemakai. Serah terima dilakukan di menu Kendaraan & alat
 * (API tetap menjaga aturan STNK/KIR/SIM, jadwal, dan bentrok).
 */
export function DailyPlanAssetsPanel({ teamId, workDate }: { teamId: string; workDate: string }) {
  const tools = useTools();
  const vehicles = useVehicles();
  const availability = useAssetAvailability(workDate, teamId || undefined);

  if (!teamId) return null;

  const rows: AssetRow[] = [
    ...(tools.data ?? []).filter((t) => t.team_id === teamId)
      .map((t) => ({ kind: "TOOL" as const, id: t.tool_id, name: t.name, status: t.status })),
    ...(vehicles.data ?? []).filter((v) => v.team_id === teamId)
      .map((v) => ({ kind: "VEHICLE" as const, id: v.vehicle_id, name: v.name, status: v.status })),
  ];

  return (
    <section aria-label="Aset tim pada tanggal jadwal" className="mb-3 rounded-md border border-line p-3">
      <SectionTitle className="mb-2 text-sm">Aset tim pada {workDate || "tanggal ini"}</SectionTitle>
      {rows.length === 0 && (
        <TextBlock className="text-sm text-mist">Belum ada kendaraan atau alat yang ditetapkan ke tim ini.</TextBlock>
      )}
      <ListBlock className="space-y-2">
        {rows.map((r) => {
          const row = availability.data?.find((a) => a.asset_id === r.id);
          const conflict = !!row?.used_by_team_id && !row.used_by_requested_team;
          const free = !conflict && !!row?.available;
          return (
            <ListEntry key={`${r.kind}-${r.id}`} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <TextBlock>{r.name} ({r.kind === "TOOL" ? "alat" : "kendaraan"})</TextBlock>
              {conflict ? (
                <TextBlock role="alert" className="text-danger">
                  Bentrok: dipakai {row?.used_by_team_name ?? "tim lain"} pada {workDate}
                </TextBlock>
              ) : free ? (
                <TextBlock className="text-success">Tersedia</TextBlock>
              ) : (
                <TextBlock className="text-mist">Tidak tersedia ({statusLabel(r.status)})</TextBlock>
              )}
            </ListEntry>
          );
        })}
      </ListBlock>
    </section>
  );
}
