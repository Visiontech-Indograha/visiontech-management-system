import { Button } from "@/components/atoms/Button";

/** Tombol keluar di layar wajib daftar wajah (satu-satunya jalan keluar selain mendaftar). */
export function FaceGateLogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <Button variant="ghost" size="sm" onClick={onLogout}>
      Keluar
    </Button>
  );
}
