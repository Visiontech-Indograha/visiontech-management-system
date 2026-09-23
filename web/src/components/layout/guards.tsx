import { Navigate, Outlet, useLocation } from "react-router-dom";
import { isAllowed, type NavItem } from "@/app/navigation";
import { useSession } from "@/app/session";

/** Wajib login; menunggu pemulihan sesi; memaksa ganti password sementara (FR-AUTH-05).
 *  Hanya UX — backend tetap menegakkan otorisasi. */
export function RequireAuth() {
  const { me, ready } = useSession();
  const { pathname } = useLocation();
  if (!ready) return <p className="p-6 text-mist">Memuat...</p>;
  if (!me) return <Navigate to="/login" replace />;
  if (me.must_change_password && pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  return <Outlet />;
}

/** Route guard berbasis permissions[] dari /me. */
export function RequireAccess({ item, children }: { item: NavItem; children: React.ReactNode }) {
  const { me } = useSession();
  if (!me || !isAllowed(item, me.permissions)) return <Navigate to="/forbidden" replace />;
  return <>{children}</>;
}
