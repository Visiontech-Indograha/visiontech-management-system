import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { AssetsTemplate, type AssetsDialog } from "@/components/templates/assets/AssetsTemplate";
import { useAssets, type Asset } from "@/services/assetService";

/** "Kendaraan & alat" (prototype/js/operations.js assets). Aturan alokasi tetap di API. */
export function AssetsPage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canManage = perms.includes("manage:assets");
  const canReserve = canManage || perms.includes("create:plan");
  // RETURN_ASSET: ketua rencana kerja peminjam (bukan petugas aset); VERIFY_RETURN: petugas aset.
  const isBorrowingLeader = (a: Asset) => !!me?.employee_id && a.leader_employee_id === me.employee_id && !canManage;
  const assets = useAssets();
  const [open, setOpen] = useState<AssetsDialog>(null);
  const close = () => setOpen(null);

  return (
    <AssetsTemplate
      assets={assets}
      canManage={canManage}
      canReserve={canReserve}
      isBorrowingLeader={isBorrowingLeader}
      open={open}
      onOpen={setOpen}
      close={close}
    />
  );
}
