import { TextBlock } from "@/components/molecules/TextBlock";
/** Judul + penjelasan layar wajib daftar wajah. */
export function FaceEnrollIntro() {
  return (
    <>
      <TextBlock as="h1" className="text-xl font-semibold">Daftarkan wajah Anda</TextBlock>
      <TextBlock className="mt-1 text-sm text-mist">
        Pendaftaran wajah wajib dilakukan sekali sebelum Anda dapat membuka menu lainnya.
      </TextBlock>
    </>
  );
}
