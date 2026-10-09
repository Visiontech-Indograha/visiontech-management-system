import clsx from "clsx";
import { Suspense, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { visibleNav } from "@/app/navigation";
import { useSession } from "@/app/session";
import { useLiveEvents } from "@/lib/liveEvents";
import { ROLE_LABEL } from "@/lib/types";
import { MobileTopBar } from "../organisms/MobileTopBar";
import { NotificationBell } from "../organisms/NotificationBell";
import { PageLoadingFallback } from "../organisms/PageLoadingFallback";
import { SidebarBrand } from "../organisms/SidebarBrand";
import { SidebarNav } from "../organisms/SidebarNav";
import { SidebarProfile } from "../organisms/SidebarProfile";

/** Kerangka aplikasi: rail kiri 232 px (ciut 64 px; di < 768 px menjadi laci) + isi halaman. */
export function AppShell() {
  const { me, logout } = useSession();
  useLiveEvents(!!me);
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const items = visibleNav(me?.permissions ?? []);
  const roleLabel = me ? (ROLE_LABEL[me.role] ?? me.role) : "";

  return (
    <div className="flex min-h-screen">
      <div className="scroll-progress" aria-hidden />
      {drawerOpen && (
        <div className="fixed inset-0 z-30 bg-scrim md:hidden" onClick={() => setDrawerOpen(false)} aria-hidden />
      )}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-sidebar-border bg-sidebar",
          "transition-[transform,width] duration-[var(--motion-base)] ease-out md:sticky md:top-0 md:h-screen md:translate-x-0",
          collapsed && "md:w-[76px]",
          drawerOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <SidebarBrand
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
          onClose={() => setDrawerOpen(false)}
        />
        <SidebarNav items={items} collapsed={collapsed} onNavigate={() => setDrawerOpen(false)} />
        {me && (
          <SidebarProfile email={me.email} roleLabel={roleLabel} collapsed={collapsed} onLogout={() => void logout()} />
        )}
      </aside>

      <div className="min-w-0 flex-1">
        <MobileTopBar onOpenMenu={() => setDrawerOpen(true)} />
        <div className="sticky top-0 z-20 hidden justify-end px-8 pt-3 md:flex lg:px-10">
          <NotificationBell className="bg-surface shadow-card ring-1 ring-line" />
        </div>
        <main className="mx-auto w-full max-w-[1320px] px-4 py-6 md:px-8 md:pb-8 md:pt-2 lg:px-10">
          <div key={pathname} className="page-enter">
            <Suspense fallback={<PageLoadingFallback />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
