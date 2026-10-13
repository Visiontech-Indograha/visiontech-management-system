import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import { useFaceStatus } from "@/services/accountService";
import { FaceEnrollRequiredPage } from "@/pages/face/FaceEnrollRequiredPage";

/** Wajib login; menunggu pemulihan sesi (UX saja — backend tetap menegakkan otorisasi). */
export function RequireAuth() {
  const { me, ready } = useSession();
  if (!ready) return <p className="p-6 text-mist">Memuat...</p>;
  if (!me) return <Navigate to="/login" replace />;
  return <RequireFace />;
}

/** Akun terhubung karyawan yang belum mendaftarkan wajah tidak boleh membuka menu lain (bila server mewajibkan).
 *  Galat/memuat TIDAK memblokir: hanya `enrollment_required` dari server yang menutup halaman. */
function RequireFace() {
  const { pathname } = useLocation();
  const status = useFaceStatus();
  if (pathname !== "/change-password" && status.data?.enrollment_required) {
    return <FaceEnrollRequiredPage status={status.data} />;
  }
  return <Outlet />;
}

