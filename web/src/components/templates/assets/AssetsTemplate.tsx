import type { UseQueryResult } from "@tanstack/react-query";
import { AssetCheckDialog } from "@/components/organisms/assets/AssetCheckDialog";
import { AssetCreateButton } from "@/components/organisms/assets/AssetCreateButton";
import { AssetCreateDialog } from "@/components/organisms/assets/AssetCreateDialog";
import { AssetList, type AssetAction } from "@/components/organisms/assets/AssetList";
import { AssetReleaseDialog } from "@/components/organisms/assets/AssetReleaseDialog";
import { AssetReserveDialog } from "@/components/organisms/assets/AssetReserveDialog";
import { AssetReturnDialog } from "@/components/organisms/assets/AssetReturnDialog";
import { AssetReturnHistoryDialog } from "@/components/organisms/assets/AssetReturnHistoryDialog";
import { AssetVerifyReturnDialog } from "@/components/organisms/assets/AssetVerifyReturnDialog";
import type { Asset } from "@/services/assetService";
import { PageTemplate } from "../PageTemplate";

/** Dialog aset yang sedang terbuka di halaman "Kendaraan & alat". */
export type AssetsDialog = { kind: "create" } | AssetAction | null;

/** Kerangka "Kendaraan & alat": kartu aset + dialog sesuai tindakan. */
export function AssetsTemplate({ assets, canManage, canReserve, isBorrowingLeader, open, onOpen, close }: {
  assets: UseQueryResult<Asset[]>;
  canManage: boolean;
  canReserve: boolean;
  isBorrowingLeader: (asset: Asset) => boolean;
  open: AssetsDialog;
  onOpen: (dialog: AssetsDialog) => void;
  close: () => void;
}) {
  return (
    <PageTemplate title="Kendaraan & alat" action={canManage && <AssetCreateButton onCreate={() => onOpen({ kind: "create" })} />}>
      <AssetList assets={assets} canManage={canManage} canReserve={canReserve} isBorrowingLeader={isBorrowingLeader} onOpen={onOpen} />
      {open?.kind === "create" && <AssetCreateDialog onClose={close} />}
      {open?.kind === "reserve" && <AssetReserveDialog asset={open.asset} onClose={close} />}
      {open?.kind === "release" && <AssetReleaseDialog asset={open.asset} onClose={close} />}
      {open?.kind === "check" && <AssetCheckDialog asset={open.asset} onClose={close} />}
      {open?.kind === "return" && <AssetReturnDialog asset={open.asset} onClose={close} />}
      {open?.kind === "verify" && <AssetVerifyReturnDialog asset={open.asset} onClose={close} />}
      {open?.kind === "history" && <AssetReturnHistoryDialog asset={open.asset} onClose={close} />}
    </PageTemplate>
  );
}
