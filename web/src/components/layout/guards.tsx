import { Navigate, Outlet } from "react-router-dom";
import { isAllowed, type NavItem } from "@/app/navigation";
import { useSession } from "@/app/session";

/** Wajib login; menunggu pemulihan sesi (UX saja — backend tetap menegakkan otorisasi). */
export function RequireAuth() {
  const { me, ready } = useSession();
  if (!ready) return <p className="p-6 text-mist">Memuat...</p>;
  if (!me) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/** Route guard berbasis permissions[] dari /me. */
export function RequireAccess({ item, children }: { item: NavItem; children: React.ReactNode }) {
  const { me } = useSession();
  if (!me || !isAllowed(item, me.permissions)) return <Navigate to="/forbidden" replace />;
  return <>{children}</>;
}
