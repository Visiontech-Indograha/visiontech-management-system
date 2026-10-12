import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Pesan bila rencana kerja belum selesai (presentasi hanya untuk pekerjaan yang sudah selesai). */
export function PresentationUnavailable({ backTo }: { backTo: string }) {
  return (
    <>
        <TextBlock as="h1" className="mb-2 text-xl font-semibold">Presentasi tidak tersedia</TextBlock>
        <TextBlock className="mb-6 text-mist">Hanya pekerjaan yang sudah selesai yang dapat dipresentasikan.</TextBlock>
        <InlineLink to={backTo} className="font-semibold text-lens hover:underline">
          Kembali
        </InlineLink>
    </>
  );
}
