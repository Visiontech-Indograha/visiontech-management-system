import { useState } from "react";
import { useSession } from "@/app/session";
import { AssetCheckDialog } from "@/components/organisms/assets/AssetCheckDialog";
import { AssetCreateButton } from "@/components/organisms/assets/AssetCreateButton";
import { AssetCreateDialog } from "@/components/organisms/assets/AssetCreateDialog";
import { AssetList, type AssetAction } from "@/components/organisms/assets/AssetList";
import { AssetReleaseDialog } from "@/components/organisms/assets/AssetReleaseDialog";
import { AssetReserveDialog } from "@/components/organisms/assets/AssetReserveDialog";
import { AssetReturnDialog } from "@/components/organisms/assets/AssetReturnDialog";
import { AssetReturnHistoryDialog } from "@/components/organisms/assets/AssetReturnHistoryDialog";
import { AssetVerifyReturnDialog } from "@/components/organisms/assets/AssetVerifyReturnDialog";
import { PageTemplate } from "@/components/templates/PageTemplate";
import { useAssets, type Asset } from "@/services/assetService";

type Open = { kind: "create" } | AssetAction | null;

/** "Kendaraan & alat" (prototype/js/operations.js assets). Aturan alokasi tetap di API. */
export function AssetsPage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canManage = perms.includes("manage:assets");
  const canReserve = canManage || perms.includes("create:plan");
  // RETURN_ASSET: ketua SK peminjam (bukan petugas aset); VERIFY_RETURN: petugas aset.
  const isBorrowingLeader = (a: Asset) => !!me?.employee_id && a.leader_employee_id === me.employee_id && !canManage;
  const assets = useAssets();
  const [open, setOpen] = useState<Open>(null);
  const close = () => setOpen(null);

  return (
    <PageTemplate title="Kendaraan & alat" action={canManage && <AssetCreateButton onCreate={() => setOpen({ kind: "create" })} />}>
      <AssetList assets={assets} canManage={canManage} canReserve={canReserve} isBorrowingLeader={isBorrowingLeader} onOpen={setOpen} />
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
