import { Navigate, Outlet, useLocation } from "react-router-dom";
import { PageSkeleton } from "@/components/molecules/PageSkeleton";
import { useSession } from "@/stores/sessionStore";
import { useFaceStatus } from "@/services/accountService";
import { FaceEnrollRequiredPage } from "@/pages/face/FaceEnrollRequiredPage";

/** Wajib login; menunggu pemulihan sesi (UX saja — backend tetap menegakkan otorisasi). */
export function RequireAuth() {
  const { me, ready } = useSession();
  const { pathname, search, hash } = useLocation();
  if (!ready) return <PageSkeleton />;
  if (!me) return <Navigate to="/login" replace state={{ from: `${pathname}${search}${hash}` }} />;
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

