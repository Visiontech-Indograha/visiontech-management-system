import clsx from "clsx";
import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, ShieldCheck, X } from "lucide-react";
import { Fragment, Suspense, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { visibleNav } from "@/app/navigation";
import { useSession } from "@/app/session";
import logo from "@/assets/brand/logo-visiontech.png";
import { Skeleton } from "@/components/atoms/Skeleton";
import { useLiveEvents } from "@/lib/liveEvents";
import { ROLE_LABEL } from "@/lib/types";
import { NotificationBell } from "../organisms/NotificationBell";

function initials(email: string) {
  const name = email.split("@")[0].replace(/[^a-z]/gi, " ").trim();
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? parts[0]?.[1] ?? "")).toUpperCase() || "V";
}

function PageFallback() {
  return (
    <div aria-busy className="space-y-4">
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

/** Rail kiri 232 px (ciut 64 px); di < 768 px menjadi laci. */
export function AppShell() {
  const { me, logout } = useSession();
  useLiveEvents(!!me);
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const items = visibleNav(me?.permissions ?? []);
  const roleLabel = me ? (ROLE_LABEL[me.role] ?? me.role) : "";

  const nav = (
    <nav aria-label="Menu utama" className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
      {items.map((item, i) => {
        const Icon = item.icon;
        const newGroup = item.group && item.group !== items[i - 1]?.group;
        return (
          <Fragment key={item.path}>
            {newGroup && !collapsed && (
              <p className="overline px-3 pb-1.5 pt-5">{item.group}</p>
            )}
            <NavLink
              to={item.path}
              end
              title={collapsed ? item.label : undefined}
              onClick={() => setDrawerOpen(false)}
              className={({ isActive }) =>
                clsx(
                  "group relative flex h-10 items-center gap-3 rounded-control px-3 text-sm font-medium",
                  "transition-colors duration-[var(--motion-fast)]",
                  isActive
                    ? "bg-surface text-lens shadow-card ring-1 ring-line before:absolute before:inset-y-2 before:-left-3 before:w-1 before:rounded-full before:bg-gold"
                    : "text-foreground hover:bg-hover hover:text-ink",
                )
              }
            >
              <Icon size={19} strokeWidth={1.75} aria-hidden className="shrink-0" />
              <span className={clsx(collapsed && "md:sr-only")}>{item.label}</span>
            </NavLink>
          </Fragment>
        );
      })}
    </nav>
  );

  const profile = me && (
    <div className="p-3">
      <div className={clsx("flex items-center gap-3 rounded-panel bg-surface p-2.5 shadow-card ring-1 ring-line", collapsed && "md:justify-center md:p-1.5")}>
        <span
          aria-hidden
          className="grid size-9 shrink-0 place-items-center rounded-full bg-accent text-sm font-semibold text-lens"
        >
          {initials(me.email)}
        </span>
        <div className={clsx("min-w-0 flex-1", collapsed && "md:sr-only")}>
          <p className="truncate text-sm font-semibold text-ink">{me.email}</p>
          <p className="text-xs text-mist">{roleLabel}</p>
        </div>
      </div>
      <NavLink
        to="/account"
        className="mt-2 flex h-10 w-full items-center gap-3 rounded-control px-3 text-sm text-mist transition-colors hover:bg-hover hover:text-ink"
      >
        <ShieldCheck size={19} strokeWidth={1.75} aria-hidden />
        <span className={clsx(collapsed && "md:sr-only")}>Akun & keamanan</span>
      </NavLink>
      <button
        type="button"
        onClick={() => void logout()}
        className="flex h-10 w-full items-center gap-3 rounded-control px-3 text-sm text-mist transition-colors hover:bg-danger-bg hover:text-danger"
      >
        <LogOut size={19} strokeWidth={1.75} aria-hidden />
        <span className={clsx(collapsed && "md:sr-only")}>Keluar</span>
      </button>
    </div>
  );

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
        <div className={clsx("flex h-16 items-center justify-between gap-2 px-4", collapsed && "md:flex-col md:justify-center md:gap-1 md:h-auto md:py-3")}>
          <span className="flex min-w-0 items-center">
            <img
              src={logo}
              alt="Visiontech Indograha"
              className={clsx("h-9 w-auto max-w-[168px] object-contain", collapsed && "md:h-auto md:max-w-[44px]")}
            />
          </span>
          <button
            type="button"
            className="hidden rounded-control p-1.5 text-mist transition-colors hover:bg-hover hover:text-ink md:block"
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
        <header className="sticky top-0 z-20 flex h-14 items-center border-b border-line bg-surface/90 px-4 backdrop-blur-sm md:hidden">
          <button
            type="button"
            className="rounded-control p-2 text-ink hover:bg-hover"
            onClick={() => setDrawerOpen(true)}
            aria-label="Buka menu"
          >
            <Menu size={20} />
          </button>
          <img src={logo} alt="Visiontech Indograha" className="ml-2 h-7 w-auto object-contain" />
          <NotificationBell className="ml-auto" />
        </header>
        <div className="sticky top-0 z-20 hidden justify-end px-8 pt-3 md:flex lg:px-10">
          <NotificationBell className="bg-surface shadow-card ring-1 ring-line" />
        </div>
        <main className="mx-auto w-full max-w-[1320px] px-4 py-6 md:px-8 md:pb-8 md:pt-2 lg:px-10">
          <div key={pathname} className="page-enter">
            <Suspense fallback={<PageFallback />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
