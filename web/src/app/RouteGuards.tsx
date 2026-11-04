import { Navigate, Outlet, useLocation } from "react-router-dom";
import { PageSkeleton } from "@/components/molecules/PageSkeleton";
import { isAllowed, type NavItem } from "@/app/navigation";
import { useSession } from "@/app/session";
import { useFaceStatus } from "@/services/accountService";
import { FaceEnrollRequiredPage } from "@/pages/face/FaceEnrollRequiredPage";

/** Wajib login; menunggu pemulihan sesi (UX saja — backend tetap menegakkan otorisasi). */
export function RequireAuth() {
  const { me, ready } = useSession();
  if (!ready) return <PageSkeleton />;
  if (!me) return <Navigate to="/login" replace />;
  return <RequireFace />;
}

/** Akun terhubung karyawan yang belum mendaftarkan wajah tidak boleh membuka menu lain (bila server mewajibkan).
 *  Galat/memuat TIDAK memblokir: hanya `required` tanpa `enrolled` dari server yang menutup halaman. */
function RequireFace() {
  const { pathname } = useLocation();
  const status = useFaceStatus();
  if (pathname !== "/change-password" && status.data?.required && !status.data.enrolled) {
    return <FaceEnrollRequiredPage />;
  }
  return <Outlet />;
}

/** Route guard berbasis permissions[] dari /me. */
export function RequireAccess({ item, children }: { item: NavItem; children: React.ReactNode }) {
  const { me } = useSession();
  if (!me || !isAllowed(item, me.permissions)) return <Navigate to="/403" replace />;
  return <>{children}</>;
}
