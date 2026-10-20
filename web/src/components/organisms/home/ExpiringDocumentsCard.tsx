import { formatDate } from "@/lib/format";
import type { ExpiringList } from "@/services/homeService";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

const URGENCY: Record<string, { label: string; tone: string }> = {
  EXPIRED: { label: "Kedaluwarsa", tone: "bg-danger-bg text-danger" },
  CRITICAL: { label: "≤ 7 hari", tone: "bg-warning-bg text-warning" },
  WARNING: { label: "≤ 30 hari", tone: "bg-info-bg text-info" },
};

/** M2: dokumen pribadi kedaluwarsa atau berakhir ≤ 30 hari (8 teratas). */
export function ExpiringDocumentsCard({ items }: { items: ExpiringList["items"] }) {
  return (
    <Panel className="gap-4">
      <PanelHeader>
        <PanelTitle className="text-heading">Dokumen mendekati kedaluwarsa</PanelTitle>
        <PanelDescription>Berakhir dalam 30 hari atau sudah lewat — unggah dokumen penggantinya.</PanelDescription>
      </PanelHeader>
      <PanelContent className="px-3 md:px-4">
        <ListBlock className="divide-y divide-line">
          {items.slice(0, 8).map((d) => (
            <ListEntry key={d.id}>
              <InlineLink
                to={`/directory/${d.employee_id}`}
                className="flex items-center gap-4 rounded-control px-3 py-3 transition-colors hover:bg-hover"
              >
                <div className="min-w-0 flex-1">
                  <TextBlock className="truncate font-medium text-ink">{d.full_name}</TextBlock>
                  <TextBlock className="mt-0.5 truncate text-body-sm text-mist">
                    {d.doc_type} · berlaku s.d. {formatDate(d.expiry_date)}
                  </TextBlock>
                </div>
                <TextBlock as="span" className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${URGENCY[d.urgency]?.tone ?? ""}`}>
                  {URGENCY[d.urgency]?.label ?? d.urgency}
                </TextBlock>
              </InlineLink>
            </ListEntry>
          ))}
        </ListBlock>
        {items.length > 8 && <TextBlock className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</TextBlock>}
      </PanelContent>
    </Panel>
  );
}
