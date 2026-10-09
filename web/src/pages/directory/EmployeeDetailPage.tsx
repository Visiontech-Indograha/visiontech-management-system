import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useSession } from "@/app/session";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useEmployee, useUnits, type Employee } from "@/services/employeeService";
import { AccountCard } from "@/components/organisms/directory/AccountCard";
import { AssignmentHistory, PromoteDialog } from "@/components/organisms/directory/AssignmentHistory";
import { DocumentsPanel } from "@/components/organisms/directory/DocumentsPanel";
import { EmployeeActions } from "@/components/organisms/directory/EmployeeActions";
import { EmployeeArchivePanel } from "@/components/organisms/directory/EmployeeArchivePanel";
import { EmployeeDetailSkeleton } from "@/components/organisms/directory/EmployeeDetailSkeleton";
import { OffboardDialog } from "@/components/organisms/directory/EmployeeLifecycleDialogs";
import { EmployeeLoadError } from "@/components/organisms/directory/EmployeeLoadError";
import { EmployeeProfileCard } from "@/components/organisms/directory/EmployeeProfileCard";
import { EmployeeProfileDialog } from "@/components/organisms/directory/EmployeeProfileDialog";

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

  if (employee.isError) return <EmployeeLoadError message={employee.error.message} />;

  if (!e) return <EmployeeDetailSkeleton />;

  return (
    <PageTemplate
      title={e.full_name}
      action={
        canEdit && (
          <EmployeeActions
            isActive={e.is_active}
            onPromote={() => setPromoting(true)}
            onOffboard={() => setOffboarding(true)}
            onEdit={() => setEditing(true)}
          />
        )
      }
    >
      <EmployeeProfileCard
        employee={e}
        unitName={units.data?.find((u) => u.id === e.unit_id)?.name ?? null}
        canSeePrivate={canSeePrivate}
      />
      {canEdit && <AccountCard employee={e} />}
      <AssignmentHistory employee={e} />
      {canEdit && !e.is_active && <EmployeeArchivePanel employee={e} />}
      {canManageDocs && <DocumentsPanel employeeId={e.id} canManage canVerify={!!me?.permissions.includes("verify:documents")} />}
      {editing && <EmployeeProfileDialog employee={e} onClose={() => setEditing(false)} />}
      {promoting && <PromoteDialog employee={e} onClose={() => setPromoting(false)} />}
      {offboarding && <OffboardDialog employee={e} onClose={() => setOffboarding(false)} />}
    </PageTemplate>
  );
}
