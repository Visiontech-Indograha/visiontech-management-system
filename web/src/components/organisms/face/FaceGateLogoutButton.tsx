import { ActionButton } from "@/components/molecules/ActionButton";

/** Tombol keluar di layar wajib daftar wajah (satu-satunya jalan keluar selain mendaftar). */
export function FaceGateLogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <ActionButton variant="ghost" size="sm" onClick={onLogout}>
      Keluar
    </ActionButton>
  );
}
