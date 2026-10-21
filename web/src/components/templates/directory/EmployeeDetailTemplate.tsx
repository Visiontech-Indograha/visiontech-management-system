import { AccountCard } from "@/components/organisms/directory/AccountCard";
import { DocumentsPanel } from "@/components/organisms/directory/DocumentsPanel";
import { EmployeeAddressesPanel } from "@/components/organisms/directory/EmployeeAddressesPanel";
import { EmployeeActions } from "@/components/organisms/directory/EmployeeActions";
import { EmployeeArchivePanel } from "@/components/organisms/directory/EmployeeArchivePanel";
import { EmployeeDetailSkeleton } from "@/components/organisms/directory/EmployeeDetailSkeleton";
import { EmployeeOffboardDialog } from "@/components/organisms/directory/EmployeeOffboardDialog";
import { EmployeeLoadError } from "@/components/organisms/directory/EmployeeLoadError";
import { EmployeeProfileCard } from "@/components/organisms/directory/EmployeeProfileCard";
import { EmployeeProfileDialog } from "@/components/organisms/directory/EmployeeProfileDialog";
import type { Employee } from "@/services/employeeService";
import { PageTemplate } from "../PageTemplate";

/** Kerangka detail karyawan: galat / memuat / profil, alamat, akun, arsip, dokumen + dialog HR. */
export function EmployeeDetailTemplate(props: {
  errorMessage: string | null;
  employee: Employee | undefined;
  canEdit: boolean;
  canManageDocs: boolean;
  canSeePrivate: boolean;
  editing: boolean;
  offboarding: boolean;
  onEdit: () => void;
  onOffboard: () => void;
  onCloseEdit: () => void;
  onCloseOffboard: () => void;
}) {
  const { errorMessage, employee: e, canEdit, canManageDocs, canSeePrivate, editing, offboarding } = props;
  if (errorMessage !== null) return <EmployeeLoadError message={errorMessage} />;

  if (!e) return <EmployeeDetailSkeleton />;

  return (
    <PageTemplate
      title={e.full_name}
      action={
        canEdit && (
          <EmployeeActions
            isActive={e.offboarding_status === "active"}
            onOffboard={props.onOffboard}
            onEdit={props.onEdit}
          />
        )
      }
    >
      <EmployeeProfileCard
        employee={e}
        canSeePrivate={canSeePrivate}
      />
      {canSeePrivate && (
        <EmployeeAddressesPanel employeeId={e.employee_id} addresses={e.addresses ?? []} canEdit={canEdit} />
      )}
      {canEdit && <AccountCard employee={e} />}
      {canEdit && e.offboarding_status === "offboarded" && <EmployeeArchivePanel employee={e} />}
      {canManageDocs && <DocumentsPanel employeeId={e.employee_id} canManage />}
      {editing && <EmployeeProfileDialog employee={e} onClose={props.onCloseEdit} />}
      {offboarding && <EmployeeOffboardDialog employee={e} onClose={props.onCloseOffboard} />}
    </PageTemplate>
  );
}
