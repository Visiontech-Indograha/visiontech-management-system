import { useSession } from "@/stores/sessionStore";
import { useFaceStatus } from "@/services/accountService";
import { FaceEnrollRequiredTemplate } from "@/components/templates/face/FaceEnrollRequiredTemplate";

/** Layar penuh yang menggantikan semua halaman sampai wajah pekerja lapangan ini terdaftar (status.required). */
export function FaceEnrollRequiredPage() {
  const { logout } = useSession();
  const { refetch } = useFaceStatus();
  return <FaceEnrollRequiredTemplate onEnrolled={() => void refetch()} onLogout={() => void logout()} />;
}
