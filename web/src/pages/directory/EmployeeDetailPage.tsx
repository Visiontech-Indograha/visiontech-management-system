import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useSession } from "@/app/session";
import { EmployeeDetailTemplate } from "@/components/templates/directory/EmployeeDetailTemplate";
import { useEmployee, useUnits, type Employee } from "@/services/employeeService";

/** Detail karyawan: profil, akun, riwayat penugasan, arsip, dan dokumen (sesuai izin). */
export function EmployeeDetailPage() {
  const { id = "" } = useParams();
  const fromList = (useLocation().state as { employee?: Employee } | null)?.employee;
  const { me } = useSession();
  const employee = useEmployee(id, fromList?.id === id ? fromList : undefined);
  const [editing, setEditing] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [offboarding, setOffboarding] = useState(false);
  const units = useUnits();
  const canEdit = !!me?.permissions.includes("manage:users");
  const canManageDocs = !!me?.permissions.includes("manage:employee_documents");
  // M2-01 (prototipe privateAccess): data kontak pribadi hanya untuk HR/admin & pemiliknya — server pun menyaringnya.
  const canSeePrivate = canManageDocs || me?.employee_id === id;
  const e = employee.data;

  return (
    <EmployeeDetailTemplate
      errorMessage={employee.isError ? employee.error.message : null}
      employee={e}
      unitName={e ? (units.data?.find((u) => u.id === e.unit_id)?.name ?? null) : null}
      canEdit={canEdit}
      canManageDocs={canManageDocs}
      canVerifyDocs={!!me?.permissions.includes("verify:documents")}
      canSeePrivate={canSeePrivate}
      editing={editing}
      promoting={promoting}
      offboarding={offboarding}
      onEdit={() => setEditing(true)}
      onPromote={() => setPromoting(true)}
      onOffboard={() => setOffboarding(true)}
      onCloseEdit={() => setEditing(false)}
      onClosePromote={() => setPromoting(false)}
      onCloseOffboard={() => setOffboarding(false)}
    />
  );
}
