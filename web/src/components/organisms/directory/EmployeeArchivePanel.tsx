import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/atoms/Button";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useArchiveEmployee, useRestoreEmployee, type Employee } from "@/services/employeeService";

/**
 * Hapus (arsip) karyawan yang sudah di-offboard dan pulihkan kembali (V-29). API tidak menampilkan
 * karyawan terhapus di daftar, jadi pemulihan tersedia di halaman ini selama detailnya masih terbuka.
 */
export function EmployeeArchivePanel({ employee }: { employee: Employee }) {
  const archive = useArchiveEmployee(employee.id);
  const restore = useRestoreEmployee(employee.id);
  const [archived, setArchived] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = archive.isPending || restore.isPending;

  const doArchive = async () => {
    setError(null);
    try {
      await archive.mutateAsync();
      setArchived(true);
      toast.success("Karyawan dihapus dari direktori.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setConfirming(false);
    }
  };
  const doRestore = async () => {
    setError(null);
    try {
      await restore.mutateAsync();
      setArchived(false);
      toast.success("Karyawan dipulihkan sebagai nonaktif.");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <section aria-label="Hapus karyawan" className="mb-8 max-w-xl rounded-panel border border-line bg-surface shadow-card p-4">
      {error && (
        <p role="alert" className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      {archived ? (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="text-sm">Karyawan ini sudah dihapus dan tidak tampil di Direktori.</p>
          <Button variant="outline" onClick={doRestore} disabled={busy}>
            Pulihkan karyawan
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-mist">Karyawan nonaktif dapat dihapus dari Direktori. Data historis tetap tersimpan.</p>
          <Button variant="outline" onClick={() => setConfirming(true)} disabled={busy}>
            Hapus karyawan
          </Button>
        </div>
      )}
      <VmsDialog
        open={confirming}
        title="Hapus karyawan?"
        onClose={() => setConfirming(false)}
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirming(false)} disabled={busy}>
              Batal
            </Button>
            <Button onClick={doArchive} disabled={busy}>
              Ya, hapus
            </Button>
          </>
        }
      >
        <p className="text-sm">
          {employee.full_name} akan disembunyikan dari Direktori. Riwayat rencana kerja, absensi, dan dokumennya tidak dihapus.
        </p>
      </VmsDialog>
    </section>
  );
}
