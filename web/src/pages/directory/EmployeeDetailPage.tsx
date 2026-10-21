import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import { EmployeeDetailTemplate } from "@/components/templates/directory/EmployeeDetailTemplate";
import { useEmployee, type Employee } from "@/services/employeeService";

/** Detail karyawan: profil, alamat, akun, arsip, dan dokumen (sesuai izin). */
export function EmployeeDetailPage() {
  const { id = "" } = useParams();
  const fromList = (useLocation().state as { employee?: Employee } | null)?.employee;
  const { me } = useSession();
  const employee = useEmployee(id, fromList?.employee_id === id ? fromList : undefined);
  const [editing, setEditing] = useState(false);
  const [offboarding, setOffboarding] = useState(false);
  const canEdit = !!me?.permissions.includes("manage:users");
  const canManageDocs = !!me?.permissions.includes("manage:employee_documents");
  // M2-01 (prototipe privateAccess): data kontak pribadi hanya untuk HR/admin & pemiliknya — server pun menyaringnya.
  const canSeePrivate = canManageDocs || me?.employee_id === id;
  const e = employee.data;

  return (
    <EmployeeDetailTemplate
      errorMessage={employee.isError ? employee.error.message : null}
      employee={e}
      canEdit={canEdit}
      canManageDocs={canManageDocs}
      canSeePrivate={canSeePrivate}
      editing={editing}
      offboarding={offboarding}
      onEdit={() => setEditing(true)}
      onOffboard={() => setOffboarding(true)}
      onCloseEdit={() => setEditing(false)}
      onCloseOffboard={() => setOffboarding(false)}
    />
  );
}
