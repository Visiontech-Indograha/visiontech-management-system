import { useEffect, type ReactNode } from "react";
import { useSession } from "../stores/sessionStore";

/** Memulihkan sesi dari cookie refresh saat aplikasi dibuka. */
export function SessionProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    useSession.getState().initSession();
  }, []);

  return <>{children}</>;
}
