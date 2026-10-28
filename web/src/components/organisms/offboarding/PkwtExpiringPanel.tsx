import { ActionButton } from "@/components/molecules/ActionButton";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { wibDate } from "@/services/dailyPlanService";
import type { PkwtExpiring } from "@/services/offboardingService";

/** PKWT yang berakhir ≤ 30 hari (atau sudah lewat) dan belum diproses — HR bisa langsung memulai offboarding. */
export function PkwtExpiringPanel({ rows, canManage, onStart }: {
  rows: PkwtExpiring[];
  canManage: boolean;
  onStart: (row: PkwtExpiring) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <section aria-label="PKWT berakhir atau segera berakhir" className="mb-4 rounded-panel border border-warning/40 bg-warning-bg/40 p-4">
      <TextBlock className="mb-2 font-semibold">PKWT berakhir atau segera berakhir</TextBlock>
      <ListBlock className="space-y-1">
        {rows.map((r) => (
          <ListEntry key={r.employee_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <TextBlock as="span">
              {`${r.full_name} (${r.employee_no}) · ${r.division_name ?? "-"} · ${r.pkwt_end_date < wibDate() ? "sudah berakhir" : "berakhir"} ${formatDate(r.pkwt_end_date)}`}
              {r.open_loans > 0 ? ` · ${r.open_loans} pinjaman aset` : ""}
            </TextBlock>
            {canManage && (
              <ActionButton size="sm" variant="outline" onClick={() => onStart(r)}>Mulai offboarding</ActionButton>
            )}
          </ListEntry>
        ))}
      </ListBlock>
    </section>
  );
}
