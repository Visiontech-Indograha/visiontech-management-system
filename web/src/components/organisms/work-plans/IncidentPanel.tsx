import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { formatDate } from "@/lib/format";
import type { WorkPlan } from "@/services/workPlanService";
import { INCIDENT_CATEGORY, INCIDENT_SEVERITY, useSessionIncidents, type Incident } from "@/services/incidentService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { IncidentResolveDialog } from "@/components/organisms/work-plans/IncidentResolveDialog";
import { SectionTitle } from "@/components/molecules/SectionTitle";

/** "Laporan Insiden / HSE" di detail rencana kerja; PM (create:plan) atau petugas aset dapat menyelesaikan. */
export function IncidentPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canResolve = !!me && (me.permissions.includes("create:plan") || me.permissions.includes("manage:assets"));
  const incidents = useSessionIncidents(plan.id).data ?? [];
  const [resolving, setResolving] = useState<Incident | null>(null);
  if (incidents.length === 0) return null;
  return (
    <section aria-label="Laporan Insiden / HSE" className="rounded-panel border border-line bg-surface shadow-card p-4">
      <SectionTitle>Laporan Insiden / HSE</SectionTitle>
      <ListBlock className="space-y-3">
        {incidents.map((i) => (
          <ListEntry key={i.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-2">
              <TextBlock as="strong" className="text-sm">
                [{INCIDENT_CATEGORY[i.category] ?? i.category}] {INCIDENT_SEVERITY[i.severity] ?? i.severity}
              </TextBlock>
              <StatusBadge status={i.status} />
            </div>
            <TextBlock className="text-sm">{i.description}</TextBlock>
            <TextBlock className="text-xs text-mist">{formatDate(i.occurred_on)}</TextBlock>
            {i.resolution_note && <TextBlock className="text-sm text-mist">Penyelesaian: {i.resolution_note}</TextBlock>}
            {canResolve && i.status !== "RESOLVED" && (
              <ActionButton size="sm" className="mt-2" onClick={() => setResolving(i)}>
                Selesaikan
              </ActionButton>
            )}
          </ListEntry>
        ))}
      </ListBlock>
      {resolving && <IncidentResolveDialog plan={plan} incident={resolving} onClose={() => setResolving(null)} />}
    </section>
  );
}

