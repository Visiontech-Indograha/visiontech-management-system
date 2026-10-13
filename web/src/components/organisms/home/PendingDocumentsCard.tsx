import { formatDate } from "@/lib/format";
import type { PendingList } from "@/services/homeService";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { ArrowRight } from "@/components/molecules/Glyphs";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** P2-5: antrean verifikasi HR — dokumen pribadi berstatus PENDING (8 terlama). */
export function PendingDocumentsCard({ items }: { items: PendingList["items"] }) {
  return (
    <Panel className="gap-4">
      <PanelHeader>
        <PanelTitle className="text-heading">Dokumen menunggu verifikasi</PanelTitle>
        <PanelDescription>Terlama dulu. Unggahan Anda sendiri diperiksa petugas lain.</PanelDescription>
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
                    {d.doc_type} · diunggah {formatDate(d.uploaded_at)}
                  </TextBlock>
                </div>
                {d.uploaded_by_me && <TextBlock as="span" className="shrink-0 text-xs text-mist">Unggahan Anda</TextBlock>}
                <ArrowRight size={18} aria-hidden className="shrink-0 text-mist" />
              </InlineLink>
            </ListEntry>
          ))}
        </ListBlock>
        {items.length > 8 && <TextBlock className="px-3 pt-2 text-body-sm text-mist">+{items.length - 8} dokumen lain.</TextBlock>}
      </PanelContent>
    </Panel>
  );
}
