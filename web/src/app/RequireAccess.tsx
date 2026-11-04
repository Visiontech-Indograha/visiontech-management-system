import { Navigate } from "react-router-dom";
import { isAllowed, type NavItem } from "@/app/navigation";
import { useSession } from "@/stores/sessionStore";

/** Route guard berbasis permissions[] dari /me. */
export function RequireAccess({ item, children }: { item: NavItem; children: React.ReactNode }) {
  const { me } = useSession();
  if (!me || !isAllowed(item, me.permissions)) return <Navigate to="/403" replace />;
  return <>{children}</>;
}
