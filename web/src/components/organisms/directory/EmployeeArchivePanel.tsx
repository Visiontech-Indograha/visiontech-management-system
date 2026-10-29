import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useArchiveEmployee, useDeleteEmployee, useRestoreEmployee, type Employee } from "@/services/employeeService";
import { DeleteConfirmButton } from "@/components/organisms/DeleteConfirmButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

/**
 * Hapus (arsip) karyawan yang sudah di-offboard dan pulihkan kembali (V-29). API tidak menampilkan
 * karyawan terhapus di daftar, jadi pemulihan tersedia di halaman ini selama detailnya masih terbuka.
 */
export function EmployeeArchivePanel({ employee }: { employee: Employee }) {
  const archive = useArchiveEmployee(employee.employee_id);
  const restore = useRestoreEmployee(employee.employee_id);
  const remove = useDeleteEmployee(employee.employee_id);
  const navigate = useNavigate();
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
      <FormErrorText message={error} className="mb-3" />
      {archived ? (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <TextBlock className="text-sm">Karyawan ini sudah dihapus dan tidak tampil di Direktori.</TextBlock>
          <ActionButton variant="outline" onClick={doRestore} disabled={busy}>
            Pulihkan karyawan
          </ActionButton>
          <DeleteConfirmButton
            label="Hapus permanen"
            title="Hapus permanen karyawan?"
            description={`${employee.full_name} beserta akun login dan data terkaitnya dihapus dari database.`}
            successText="Karyawan dihapus permanen."
            onDelete={async () => {
              await remove.mutateAsync();
              navigate("/directory", { replace: true }); // detail karyawan yang sudah tidak ada jangan tetap terbuka
            }}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <TextBlock className="text-sm text-mist">Karyawan nonaktif dapat dihapus dari Direktori. Data historis tetap tersimpan.</TextBlock>
          <ActionButton variant="outline" onClick={() => setConfirming(true)} disabled={busy}>
            Hapus karyawan
          </ActionButton>
        </div>
      )}
      <VmsDialog
        open={confirming}
        title="Hapus karyawan?"
        onClose={() => setConfirming(false)}
        footer={
          <>
            <ActionButton variant="outline" onClick={() => setConfirming(false)} disabled={busy}>
              Batal
            </ActionButton>
            <ActionButton onClick={doArchive} disabled={busy}>
              Ya, hapus
            </ActionButton>
          </>
        }
      >
        <TextBlock className="text-sm">
          {employee.full_name} akan disembunyikan dari Direktori. Riwayat rencana kerja, absensi, dan dokumennya tidak dihapus.
        </TextBlock>
      </VmsDialog>
    </section>
  );
}
