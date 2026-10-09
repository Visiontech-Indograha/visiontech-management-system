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
import type { Employee } from "@/services/employeeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka detail karyawan: galat / memuat / profil, akun, penugasan, arsip, dokumen + dialog HR. */
export function EmployeeDetailTemplate(props: {
  errorMessage: string | null;
  employee: Employee | undefined;
  unitName: string | null;
  canEdit: boolean;
  canManageDocs: boolean;
  canVerifyDocs: boolean;
  canSeePrivate: boolean;
  editing: boolean;
  promoting: boolean;
  offboarding: boolean;
  onEdit: () => void;
  onPromote: () => void;
  onOffboard: () => void;
  onCloseEdit: () => void;
  onClosePromote: () => void;
  onCloseOffboard: () => void;
}) {
  const { errorMessage, employee: e, unitName, canEdit, canManageDocs, canVerifyDocs, canSeePrivate, editing, promoting, offboarding } = props;
  if (errorMessage !== null) return <EmployeeLoadError message={errorMessage} />;

  if (!e) return <EmployeeDetailSkeleton />;

  return (
    <PageTemplate
      title={e.full_name}
      action={
        canEdit && (
          <EmployeeActions
            isActive={e.is_active}
            onPromote={props.onPromote}
            onOffboard={props.onOffboard}
            onEdit={props.onEdit}
          />
        )
      }
    >
      <EmployeeProfileCard
        employee={e}
        unitName={unitName}
        canSeePrivate={canSeePrivate}
      />
      {canEdit && <AccountCard employee={e} />}
      <AssignmentHistory employee={e} />
      {canEdit && !e.is_active && <EmployeeArchivePanel employee={e} />}
      {canManageDocs && <DocumentsPanel employeeId={e.id} canManage canVerify={canVerifyDocs} />}
      {editing && <EmployeeProfileDialog employee={e} onClose={props.onCloseEdit} />}
      {promoting && <PromoteDialog employee={e} onClose={props.onClosePromote} />}
      {offboarding && <OffboardDialog employee={e} onClose={props.onCloseOffboard} />}
    </PageTemplate>
  );
}
