import { DocumentsPanel } from "@/components/organisms/directory/DocumentsPanel";
import { UnlinkedEmployeeNotice } from "@/components/organisms/directory/UnlinkedEmployeeNotice";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Berkas saya": panel berkas milik sendiri, atau pemberitahuan bila akun belum terhubung karyawan. */
export function MyDocumentsTemplate({ employeeId, canManage }: { employeeId: string | null; canManage: boolean }) {
  return (
    <PageTemplate title="Berkas saya">
      {employeeId ? (
        // M2: karyawan mengajukan dokumen pribadinya sendiri (izin dasar upload:documents); HR memverifikasi.
        <DocumentsPanel employeeId={employeeId} canManage={canManage} canRenew />
      ) : (
        <UnlinkedEmployeeNotice />
      )}
    </PageTemplate>
  );
}
