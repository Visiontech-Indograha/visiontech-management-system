import clsx from "clsx";
import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { Fragment, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { visibleNav } from "@/app/navigation";
import { useSession } from "@/app/session";
import { IncompleteDocumentsBanner } from "@/features/directory/MyDocuments";

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  team_leader: "Team Leader",
  finance: "Finance",
  hes: "HES",
  WTL: "WTL",
  DRIVER: "Driver",
};

/** Rail kiri 232 px (ciut 64 px); di < 768 px menjadi laci. */
export function AppShell() {
  const { me, logout } = useSession();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const items = visibleNav(me?.permissions ?? []);
  const roleLabel = me ? ROLE_LABEL[me.user_type ?? me.role] : "";

  const nav = (
    <nav aria-label="Menu utama" className="flex-1 overflow-y-auto px-2 py-3">
      {items.map((item, i) => {
        const Icon = item.icon;
        const newGroup = item.group && item.group !== items[i - 1]?.group;
        return (
          <Fragment key={item.path}>
            {newGroup && !collapsed && (
              <p className="px-3 pb-1 pt-4 text-xs font-semibold text-mist">{item.group}</p>
            )}
            <NavLink
              to={item.path}
              end
              title={collapsed ? item.label : undefined}
              onClick={() => setDrawerOpen(false)}
              className={({ isActive }) =>
                clsx(
                  "flex h-10 items-center gap-3 rounded-control px-3 text-sm font-medium",
                  "transition-colors duration-[var(--motion-fast)]",
                  isActive ? "bg-lens-soft text-lens" : "text-ink hover:bg-hover",
                )
              }
            >
              <Icon size={20} strokeWidth={1.75} aria-hidden />
              <span className={clsx(collapsed && "md:sr-only")}>{item.label}</span>
            </NavLink>
          </Fragment>
        );
      })}
    </nav>
  );

  const profile = me && (
    <div className="border-t border-line p-3">
      <div className={clsx("mb-2 min-w-0", collapsed && "md:sr-only")}>
        <p className="truncate text-sm font-semibold">{me.full_name}</p>
        <p className="text-xs text-mist">{roleLabel}</p>
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        className="flex h-10 w-full items-center gap-3 rounded-control px-3 text-sm text-mist hover:bg-hover"
      >
        <LogOut size={20} strokeWidth={1.75} aria-hidden />
        <span className={clsx(collapsed && "md:sr-only")}>Keluar</span>
      </button>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      {drawerOpen && (
        <div className="fixed inset-0 z-30 bg-ink/40 md:hidden" onClick={() => setDrawerOpen(false)} aria-hidden />
      )}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex w-[232px] flex-col border-r border-line bg-surface",
          "transition-transform duration-[var(--motion-base)] ease-out md:static md:translate-x-0",
          collapsed && "md:w-16",
          drawerOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between px-4">
          <span className={clsx("text-lg font-bold text-lens", collapsed && "md:sr-only")}>VMS</span>
          <button
            type="button"
            className="hidden rounded-control p-1 text-mist hover:bg-hover md:block"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Perluas menu" : "Ciutkan menu"}
          >
            {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
          </button>
          <button
            type="button"
            className="rounded-control p-1 text-mist hover:bg-hover md:hidden"
            onClick={() => setDrawerOpen(false)}
            aria-label="Tutup menu"
          >
            <X size={20} />
          </button>
        </div>
        {nav}
        {profile}
      </aside>

      <div className="min-w-0 flex-1">
        <header className="flex h-14 items-center border-b border-line bg-surface px-4 md:hidden">
          <button
            type="button"
            className="rounded-control p-2 text-ink hover:bg-hover"
            onClick={() => setDrawerOpen(true)}
            aria-label="Buka menu"
          >
            <Menu size={20} />
          </button>
          <span className="ml-2 font-bold text-lens">VMS</span>
        </header>
        <IncompleteDocumentsBanner />
        <main className="mx-auto w-full max-w-[1280px] px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
