/** Pemberitahuan di atas form revisi: dampak menyimpan revisi sesuai status rencana kerja. */
export function PlanReviseNotice({ status }: { status: unknown }) {
  return (
        <p className="mb-4 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">
          {status === "IN_PROGRESS"
            ? "Rencana kerja sedang berjalan: hari yang laporannya sudah dikirim/disetujui tidak berubah dan tanggal mulai tetap. "
            : ""}
          Setelah disimpan, dokumen versi baru terbit dengan tanda tangan Anda.{" "}
          {status === "PUBLISHED" || status === "APPEALED"
            ? "Ketua tim masih perlu menerimanya sekali."
            : "Versi baru langsung berlaku; ketua dan anggota mendapat pemberitahuan."}
        </p>
  );
}
