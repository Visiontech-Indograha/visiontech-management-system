import { useSession } from "@/app/session";
import { PageHeader } from "@/components/molecules/PageHeader";
import { DocumentsPanel } from "../components/DocumentsPanel";

/** "Berkas saya": berkas milik sendiri via /employees/{employee_id}/documents (employee_id dari /auth/me). */
export function MyDocumentsPage() {
  const { me } = useSession();
  const employeeId = me?.employee_id ?? null;
  return (
    <>
      <PageHeader title="Berkas saya" />
      {employeeId ? (
        // M2: karyawan mengajukan dokumen pribadinya sendiri (izin dasar upload:documents); HR memverifikasi.
        <DocumentsPanel employeeId={employeeId} canManage={!!me?.permissions.includes("upload:documents")} canRenew />
      ) : (
        <p className="rounded-panel border border-line bg-surface shadow-card px-4 py-6 text-center text-mist">
          Akun Anda belum terhubung dengan data karyawan, jadi belum ada berkas untuk ditampilkan.
        </p>
      )}
    </>
  );
}
