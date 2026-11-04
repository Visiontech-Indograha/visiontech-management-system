import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useEmployeeFaceStatus, useResetEmployeeFace, type Employee } from "@/services/employeeService";

/**
 * Status pengenalan wajah karyawan (HR/admin). "Atur ulang wajah" menghapus wajah terdaftar
 * agar karyawan bisa mendaftar ulang, misalnya setelah ganti HP.
 */
export function EmployeeFaceCard({ employee }: { employee: Employee }) {
  const status = useEmployeeFaceStatus(employee.employee_id);
  const reset = useResetEmployeeFace(employee.employee_id);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const s = status.data;

  const doReset = async () => {
    setError(null);
    try {
      await reset.mutateAsync();
      toast.success("Wajah diatur ulang. Karyawan bisa mendaftar ulang.");
      setConfirming(false);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <section aria-label="Pengenalan wajah" className="mb-8 max-w-xl">
      <SectionTitle>Pengenalan wajah</SectionTitle>
      <div className="flex flex-col gap-3 rounded-panel border border-line bg-surface px-5 py-4 text-sm shadow-card">
        {status.isPending && <LoadingBar className="h-6 w-2/3" />}
        {status.isError && <TextBlock className="text-danger">Status wajah tidak dapat dimuat.</TextBlock>}
        {s && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {s.enrolled ? (
                <Pill tone="success" data-testid="face-status">Wajah terdaftar</Pill>
              ) : s.required ? (
                <Pill tone="warning" data-testid="face-status">Belum terdaftar</Pill>
              ) : (
                <Pill tone="neutral" data-testid="face-status">Tidak diwajibkan</Pill>
              )}
            </div>
            <TextBlock className="text-mist">
              {s.enrolled && s.enrolled_at
                ? `Didaftarkan pada ${formatDateTime(s.enrolled_at)}.`
                : s.enrolled
                  ? "Wajah sudah terdaftar."
                  : s.required
                    ? "Karyawan belum mendaftarkan wajah. Pendaftaran dilakukan sendiri lewat aplikasi HP."
                    : "Pengenalan wajah hanya diwajibkan untuk karyawan lapangan yang absen lewat aplikasi HP."}
            </TextBlock>
            {s.enrolled && (
              <ActionButton
                variant="outline"
                className="self-start"
                disabled={reset.isPending}
                onClick={() => setConfirming(true)}
              >
                Atur ulang wajah
              </ActionButton>
            )}
          </>
        )}
        <FormErrorText message={error} className="mb-0" />
      </div>
      <VmsDialog
        open={confirming}
        title="Atur ulang wajah?"
        onClose={() => !reset.isPending && setConfirming(false)}
        footer={
          <>
            <ActionButton variant="outline" onClick={() => setConfirming(false)} disabled={reset.isPending}>
              Batal
            </ActionButton>
            <ActionButton onClick={doReset} disabled={reset.isPending}>
              Ya, atur ulang
            </ActionButton>
          </>
        }
      >
        <TextBlock className="text-sm">
          Wajah terdaftar {employee.full_name} dihapus. Karyawan harus mendaftar ulang dengan 3–5 foto dari sudut berbeda
          sebelum bisa absen lewat aplikasi HP. Tindakan ini dicatat di riwayat aktivitas.
        </TextBlock>
      </VmsDialog>
    </section>
  );
}
