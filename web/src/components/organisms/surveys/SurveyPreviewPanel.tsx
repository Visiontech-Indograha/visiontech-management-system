import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FrameView } from "@/components/molecules/FrameView";
import { Loader2, RefreshCw } from "@/components/molecules/Glyphs";
import { ExternalLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { fetchSurveyPreview } from "@/services/surveyService";

/** Pratinjau laporan survei di halaman (PDF, sama dengan dokumen akhir). Tidak tersimpan di registri dokumen.
 * `version` berubah setiap survei berubah (titik ditambah, disetujui …) → pratinjau dimuat ulang otomatis. */
export function SurveyPreviewPanel({ taskId, version }: { taskId: string; version: string }) {
  const preview = useQuery({
    queryKey: ["surveys", taskId, "preview", version],
    queryFn: () => fetchSurveyPreview(taskId),
    staleTime: Infinity,
    retry: false,
  });
  const url = useMemo(() => (preview.data ? URL.createObjectURL(preview.data.blob) : null), [preview.data]);
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  const busy = preview.isFetching;

  return (
    <section aria-label="Pratinjau laporan" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TextBlock className="text-sm text-mist">
          Pratinjau sama persis dengan dokumen akhir (kop, tabel, foto). Tidak tercatat sebagai dokumen resmi.
        </TextBlock>
        <div className="flex flex-wrap items-center gap-3">
          {url && preview.data?.isPdf && (
            <ExternalLink href={url} target="_blank" rel="noopener" className="text-sm text-lens underline">
              Buka PDF di tab baru
            </ExternalLink>
          )}
          <ActionButton size="sm" variant="outline" onClick={() => void preview.refetch()} disabled={busy}>
            {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1.5 h-4 w-4" />}
            Muat ulang
          </ActionButton>
        </div>
      </div>
      {preview.isError && (
        <TextBlock role="alert" className="text-sm text-danger">{errorMessage(preview.error)}</TextBlock>
      )}
      {busy && !url && <TextBlock className="text-sm text-mist">Menyiapkan pratinjau… (sekitar 10 detik)</TextBlock>}
      {url && preview.data?.isPdf && (
        <FrameView title="Pratinjau laporan survei" src={url} className="h-[65vh] w-full rounded-panel border border-line" />
      )}
      {url && preview.data && !preview.data.isPdf && (
        <TextBlock className="text-sm">
          Server belum punya konverter PDF.{" "}
          <ExternalLink href={url} download="pratinjau-survei.docx" className="text-lens underline">
            Unduh pratinjau (.docx)
          </ExternalLink>
        </TextBlock>
      )}
    </section>
  );
}
