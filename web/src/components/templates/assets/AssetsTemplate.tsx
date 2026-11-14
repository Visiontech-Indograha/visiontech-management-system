import { AssetCreateButton } from "@/components/organisms/assets/AssetCreateButton";
import { BorrowersDialog } from "@/components/organisms/assets/BorrowersDialog";
import { AssetCreateDialog } from "@/components/organisms/assets/AssetCreateDialog";
import { AssetLendDialog } from "@/components/organisms/assets/AssetLendDialog";
import { AssetLendExternalDialog } from "@/components/organisms/assets/AssetLendExternalDialog";
import { AssetList, type AssetAction } from "@/components/organisms/assets/AssetList";
import { LoanRequestsPanel } from "@/components/organisms/assets/LoanRequestsPanel";
import { AssetReturnDialog } from "@/components/organisms/assets/AssetReturnDialog";
import { AssetStatusDialog } from "@/components/organisms/assets/AssetStatusDialog";
import { VehicleDriversDialog } from "@/components/organisms/vehicle-docs/VehicleDriversDialog";
import { VehicleFilesDialog } from "@/components/organisms/assets/VehicleFilesDialog";
import type { AssetKind } from "@/services/assetService";
import { PageTemplate } from "../PageTemplate";

/** Dialog aset yang sedang terbuka di halaman "Kendaraan & alat". */
export type AssetsDialog = { kind: "create"; asset: AssetKind } | { kind: "borrowers" } | AssetAction | null;

/** Kerangka "Kendaraan & alat": tab inventaris + dialog sesuai tindakan. */
export function AssetsTemplate({ canManage, open, onOpen, close }: {
  canManage: boolean;
  open: AssetsDialog;
  onOpen: (dialog: AssetsDialog) => void;
  close: () => void;
}) {
  return (
    <PageTemplate title="Kendaraan dan alat" action={canManage && <AssetCreateButton onCreate={(asset) => onOpen({ kind: "create", asset })} onBorrowers={() => onOpen({ kind: "borrowers" })} />}>
      {canManage && <LoanRequestsPanel onReceive={(loan) => onOpen({ kind: "return", loan })} />}
      <AssetList canManage={canManage} onOpen={onOpen} />
      {open?.kind === "drivers" && <VehicleDriversDialog vehicleId={open.vehicle.vehicle_id} plate={open.vehicle.number_plate} onClose={close} />}
      {open?.kind === "borrowers" && <BorrowersDialog onClose={close} />}
      {open?.kind === "create" && <AssetCreateDialog kind={open.asset} onClose={close} />}
      {open?.kind === "lend" && <AssetLendDialog kind={open.asset} assetId={open.id} assetName={open.name} onClose={close} />}
      {open?.kind === "lend-external" && <AssetLendExternalDialog kind={open.asset} assetId={open.id} assetName={open.name} onClose={close} />}
      {open?.kind === "status" && <AssetStatusDialog kind={open.asset} id={open.id} name={open.name} status={open.status} onClose={close} />}
      {open?.kind === "files" && <VehicleFilesDialog vehicle={open.vehicle} canManage={canManage} onClose={close} />}
      {open?.kind === "return" && <AssetReturnDialog loan={open.loan} onClose={close} />}
    </PageTemplate>
  );
}
