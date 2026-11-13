import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Download } from "@/components/molecules/Glyphs";
import { downloadWorkOrderExport } from "@/services/workOrderService";

const BTN = "text-xs justify-start h-11 px-2 bg-card hover:bg-surface-elevated";

/** Surat serah terima (PDF/Word): hanya tampil setelah pekerjaan selesai dan disahkan PM. */
export function BastDownloadButtons({ id, number }: { id: string; number: string }) {
  const name = `Berita_Acara_Serah_Terima_${number}`;
  return (
    <>
      <ActionButton type="button" variant="outline" size="sm" className={BTN}
        onClick={() => downloadWorkOrderExport(id, "pdf", `${name}.pdf`)}>
        <Download className="h-3 w-3 mr-1.5 text-primary shrink-0" />
        <TextBlock as="span" className="truncate">Surat serah terima (.pdf)</TextBlock>
      </ActionButton>
      <ActionButton type="button" variant="outline" size="sm" className={BTN}
        onClick={() => downloadWorkOrderExport(id, "docx", `${name}.docx`)}>
        <Download className="h-3 w-3 mr-1.5 text-blue-500 shrink-0" />
        <TextBlock as="span" className="truncate">Surat serah terima (.docx)</TextBlock>
      </ActionButton>
    </>
  );
}
