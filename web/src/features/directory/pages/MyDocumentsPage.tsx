import { useSession } from "@/app/session";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { DocumentsPanel } from "../components/DocumentsPanel";
import { UnlinkedEmployeeNotice } from "../components/UnlinkedEmployeeNotice";

/** "Berkas saya": berkas milik sendiri via /employees/{employee_id}/documents (employee_id dari /auth/me). */
export function MyDocumentsPage() {
  const { me } = useSession();
  const employeeId = me?.employee_id ?? null;
  return (
    <PageTemplate title="Berkas saya">
      {employeeId ? (
        // M2: karyawan mengajukan dokumen pribadinya sendiri (izin dasar upload:documents); HR memverifikasi.
        <DocumentsPanel employeeId={employeeId} canManage={!!me?.permissions.includes("upload:documents")} canRenew />
      ) : (
        <UnlinkedEmployeeNotice />
      )}
    </PageTemplate>
  );
}
