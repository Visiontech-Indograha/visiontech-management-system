import type { ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import type { UseQueryResult } from "@tanstack/react-query";
import { OffboardingAddButton } from "@/components/organisms/offboarding/OffboardingAddButton";
import { OffboardingDetailDialog } from "@/components/organisms/offboarding/OffboardingDetailDialog";
import { OffboardingFormDialog } from "@/components/organisms/offboarding/OffboardingFormDialog";
import { OffboardingList } from "@/components/organisms/offboarding/OffboardingList";
import { PkwtExpiringPanel } from "@/components/organisms/offboarding/PkwtExpiringPanel";
import type { Offboarding, PkwtExpiring } from "@/services/offboardingService";
import { PageTemplate } from "../PageTemplate";

export type OffboardingDialog =
  | { kind: "create"; employee?: { id: string; name: string } }
  | { kind: "detail"; id: string }
  | null;

/** Kerangka "Offboarding & Clearance" (docs/35 §7): PKWT segera berakhir, daftar proses, detail & persetujuan. */
export function OffboardingTemplate({ controls, offboardings, expiring, canManage, canApprovePm, dialog, onDialog }: {
  controls: ListControls;
  offboardings: UseQueryResult<Paged<Offboarding>>;
  expiring: PkwtExpiring[];
  canManage: boolean;
  canApprovePm: boolean;
  dialog: OffboardingDialog;
  onDialog: (d: OffboardingDialog) => void;
}) {
  const add = () => onDialog({ kind: "create" });
  return (
    <PageTemplate title="Offboarding dan Clearance" action={canManage && <OffboardingAddButton onAdd={add} />}>
      <PkwtExpiringPanel rows={expiring} canManage={canManage}
                         onStart={(r) => onDialog({ kind: "create", employee: { id: r.employee_id, name: r.full_name } })} />
      <OffboardingList controls={controls} offboardings={offboardings} canManage={canManage} onAdd={add}
                       onOpen={(id) => onDialog({ kind: "detail", id })} />
      {dialog?.kind === "create" && <OffboardingFormDialog employee={dialog.employee} onClose={() => onDialog(null)} />}
      {dialog?.kind === "detail" && (
        <OffboardingDetailDialog offboardingId={dialog.id} canManage={canManage} canApprovePm={canApprovePm}
                                 onClose={() => onDialog(null)} />
      )}
    </PageTemplate>
  );
}
