import { useSession } from "@/stores/sessionStore";
import { MyDocumentsTemplate } from "@/components/templates/directory/MyDocumentsTemplate";

/** "Berkas saya": berkas milik sendiri via /employees/{employee_id}/documents (employee_id dari /auth/me). */
export function MyDocumentsPage() {
  const { me } = useSession();
  return (
    <MyDocumentsTemplate
      employeeId={me?.employee_id ?? null}
      canManage={!!me?.permissions.includes("manage:employee_documents")}
    />
  );
}
