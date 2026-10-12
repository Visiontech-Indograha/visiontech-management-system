import { TextBlock } from "@/components/molecules/TextBlock";
/** Pemberitahuan untuk akun yang belum terhubung dengan data karyawan (halaman "Berkas saya"). */
export function UnlinkedEmployeeNotice() {
  return (
    <TextBlock className="rounded-panel border border-line bg-surface shadow-card px-4 py-6 text-center text-mist">
      Akun Anda belum terhubung dengan data karyawan, jadi belum ada berkas untuk ditampilkan.
    </TextBlock>
  );
}
