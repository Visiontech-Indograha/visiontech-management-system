import { VehicleDocsTemplate } from "@/components/templates/vehicle-docs/VehicleDocsTemplate";
import { useSession } from "@/stores/sessionStore";

/** Dokumen kendaraan untuk HSE, OM, dan SA. Mengubah butuh izin kelola. */
export function VehicleDocsPage() {
  const { me } = useSession();
  return <VehicleDocsTemplate canManage={(me?.permissions ?? []).includes("manage:vehicle_documents")} />;
}
