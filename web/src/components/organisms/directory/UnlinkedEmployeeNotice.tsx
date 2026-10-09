/** Pemberitahuan untuk akun yang belum terhubung dengan data karyawan (halaman "Berkas saya"). */
export function UnlinkedEmployeeNotice() {
  return (
    <p className="rounded-panel border border-line bg-surface shadow-card px-4 py-6 text-center text-mist">
      Akun Anda belum terhubung dengan data karyawan, jadi belum ada berkas untuk ditampilkan.
    </p>
  );
}
