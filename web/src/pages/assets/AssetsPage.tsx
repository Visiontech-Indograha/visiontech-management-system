import { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { canManageAssets } from "@/lib/aksiPeran";
import { AssetsTemplate, type AssetsDialog } from "@/components/templates/assets/AssetsTemplate";

/** "Kendaraan & alat" (Milestone 4): inventaris + serah terima. Aturan STNK/KIR/SIM & status ada di API. */
export function AssetsPage() {
  const { me } = useSession();
  const canManage = canManageAssets(me?.permissions ?? []);
  const [open, setOpen] = useState<AssetsDialog>(null);
  return <AssetsTemplate canManage={canManage} open={open} onOpen={setOpen} close={() => setOpen(null)} />;
}
