import { DocumentsPanel } from "@/components/organisms/directory/DocumentsPanel";
import { UnlinkedEmployeeNotice } from "@/components/organisms/directory/UnlinkedEmployeeNotice";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Berkas saya": panel berkas milik sendiri, atau pemberitahuan bila akun belum terhubung karyawan. */
export function MyDocumentsTemplate({ employeeId, canManage }: { employeeId: string | null; canManage: boolean }) {
  return (
    <PageTemplate title="Berkas saya">
      {employeeId ? (
        // Karyawan melihat dokumennya sendiri; HR/GA yang mencatat & memperbarui (manage:employee_documents).
        <DocumentsPanel employeeId={employeeId} canManage={canManage} />
      ) : (
        <UnlinkedEmployeeNotice />
      )}
    </PageTemplate>
  );
}
