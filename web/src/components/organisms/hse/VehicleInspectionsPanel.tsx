import { useState, type ReactNode } from "react";
import { ActionButton } from "@/components/molecules/ActionButton";
import { VehicleInspectionCreateDialog } from "@/components/organisms/hse/VehicleInspectionCreateDialog";
import { VehicleInspectionDetailDialog } from "@/components/organisms/hse/VehicleInspectionDetailDialog";
import { VehicleInspectionList } from "@/components/organisms/hse/VehicleInspectionList";
import { useSession } from "@/stores/sessionStore";

/** Isi halaman Inspeksi kendaraan: tab "Semua inspeksi" (pemegang izin lihat) dan "Inspeksi saya", tombol Buat, detail. */
export function VehicleInspectionsPanel({ renderPage }: { renderPage: (page: { action: ReactNode; body: ReactNode }) => ReactNode }) {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canSeeAll = perms.includes("view:vehicle_inspections") || perms.includes("manage:vehicle_inspections");
  const canManage = perms.includes("manage:vehicle_inspections");
  const [tab, setTab] = useState<"all" | "mine">(canSeeAll ? "all" : "mine");
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const mine = !canSeeAll || tab === "mine";
  const action = <ActionButton onClick={() => setCreating(true)}>Buat inspeksi</ActionButton>;
  const body = (
    <>
      {canSeeAll && (
        <div className="mb-4 flex gap-2" role="group" aria-label="Pilih daftar">
          <ActionButton variant={tab === "all" ? "default" : "outline"} aria-pressed={tab === "all"} onClick={() => setTab("all")}>Semua inspeksi</ActionButton>
          <ActionButton variant={tab === "mine" ? "default" : "outline"} aria-pressed={tab === "mine"} onClick={() => setTab("mine")}>Inspeksi saya</ActionButton>
        </div>
      )}
      <VehicleInspectionList key={mine ? "mine" : "all"} mine={mine} onOpen={setOpenId} onCreate={() => setCreating(true)} canCreate />
      {creating && <VehicleInspectionCreateDialog onClose={() => setCreating(false)} />}
      {openId && <VehicleInspectionDetailDialog id={openId} canVerify={canManage} onClose={() => setOpenId(null)} />}
    </>
  );
  return <>{renderPage({ action, body })}</>;
}
