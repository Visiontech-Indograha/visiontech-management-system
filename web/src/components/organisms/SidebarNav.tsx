import clsx from "clsx";
import { Fragment } from "react";
import { NavLink } from "react-router-dom";
import type { NavItem } from "@/app/navigation";

/** Menu utama di rail kiri, dikelompokkan per `group`; label disembunyikan saat rail diciutkan. */
export function SidebarNav({ items, collapsed, onNavigate }: {
  items: NavItem[];
  collapsed: boolean;
  /** Dipanggil saat menu dipilih (menutup laci di ponsel). */
  onNavigate: () => void;
}) {
  return (
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
              onClick={onNavigate}
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
}
