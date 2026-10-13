import { TextBlock } from "@/components/molecules/TextBlock";
/** Judul halaman verifikasi tanda tangan. */
export function VerifyIntro() {
  return (
    <>
      <TextBlock as="h1" className="mb-1 text-2xl font-semibold">Verifikasi tanda tangan</TextBlock>
      <TextBlock className="mb-6 text-mist">PT Visiontech — pemeriksaan keaslian dokumen ber-QR.</TextBlock>
    </>
  );
}
