import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ExportFormatButtons } from "@/components/organisms/ExportFormatButtons";
import { Download } from "@/components/molecules/Glyphs";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import {
  COMPLETION_TEMPLATES,
  downloadExport,
  useCompletionExports,
  useExportCompletion,
  type ExportRecord,
} from "@/services/exportService";

const LABEL: Record<string, string> = Object.fromEntries(COMPLETION_TEMPLATES.map((t) => [t.template, t.label]));

/** Ekspor dokumen resmi order (docs/35 §8) + riwayat yang bisa diunduh ulang. PDF resmi hanya setelah PM mengesahkan. */
export function WorkCompletionExportPanel({ completionId, signed }: { completionId: string; signed: boolean }) {
  const history = useCompletionExports(completionId);
  const exporter = useExportCompletion(completionId);

  const again = async (record: ExportRecord) => {
    try {
      await downloadExport(record);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <section aria-label="Ekspor dokumen" className="space-y-3 rounded-panel border border-primary/20 bg-primary/5 p-4">
      <div>
        <TextBlock className="font-semibold text-ink">Ekspor dokumen resmi</TextBlock>
        <TextBlock className="text-xs text-mist">
          Setiap dokumen tercatat dan bisa diunduh ulang. PDF ber-QR verifikasi tersedia setelah PM menandatangani.
        </TextBlock>
      </div>
      <div className="flex flex-col items-start gap-2">
        {COMPLETION_TEMPLATES.map((t) =>
          t.formats ? (
            <ExportFormatButtons
              key={t.template}
              label={t.label}
              busy={exporter.isPending}
              pendingFormat={exporter.variables?.template === t.template ? exporter.variables.format : null}
              onPick={(format) =>
                exporter.mutate(
                  { template: t.template, format },
                  {
                    onSuccess: () => toast.success(`${t.label} berhasil dibuat.`),
                    onError: (err) => toast.error(errorMessage(err)),
                  },
                )
              }
            />
          ) : (
            <ActionButton
              key={t.template}
              size="sm"
              variant="outline"
              disabled={exporter.isPending || (t.needsSignature && !signed)}
              onClick={() =>
                exporter.mutate(
                  { template: t.template },
                  {
                    onSuccess: () => toast.success(`${t.label} berhasil dibuat.`),
                    onError: (err) => toast.error(errorMessage(err)),
                  },
                )
              }
            >
              <Download className="mr-1.5 h-3.5 w-3.5" />
              {t.label}
            </ActionButton>
          ),
        )}
      </div>
      {(history.data?.length ?? 0) > 0 && (
        <div>
          <TextBlock className="mb-1 text-xs font-medium text-mist">Riwayat dokumen</TextBlock>
          <ListBlock className="divide-y divide-line rounded-control border border-line bg-surface">
            {history.data!.map((r) => (
              <ListEntry key={r.export_id} className="flex items-center justify-between gap-2 px-3 py-2 text-xs">
                <TextBlock as="span">
                  {`${LABEL[r.template_type] ?? r.template_type} · ${formatDateTime(r.create_at)} · ${r.generated_by_name ?? "-"}`}
                </TextBlock>
                <ActionButton size="sm" variant="ghost" onClick={() => void again(r)}>
                  Unduh
                </ActionButton>
              </ListEntry>
            ))}
          </ListBlock>
        </div>
      )}
    </section>
  );
}
