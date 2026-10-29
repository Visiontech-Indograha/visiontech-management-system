import clsx from "clsx";
import { Fragment } from "react";
import type { NavItem } from "@/app/navigation";
import { MenuLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

/** Menu utama di rail kiri, dikelompokkan per `group`; label disembunyikan saat rail diciutkan. */
export function SidebarNav({ items, collapsed, onNavigate, badges = {} }: {
  items: NavItem[];
  /** Jumlah antrean per path menu (dari /home/summary); 0 atau kosong = tanpa lencana. */
  badges?: Record<string, number>;
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
              <TextBlock className="overline px-3 pb-1.5 pt-5">{item.group}</TextBlock>
            )}
            <MenuLink
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
              <TextBlock as="span" className={clsx(collapsed && "md:sr-only")}>{item.label}</TextBlock>
              {(badges[item.path] ?? 0) > 0 && (
                <TextBlock
                  as="span"
                  aria-label={`${badges[item.path]} menunggu`}
                  className={clsx(
                    "rounded-full bg-gold px-1.5 text-xs font-semibold text-ink",
                    collapsed ? "absolute right-1.5 top-1.5 md:min-w-4 md:text-center" : "ml-auto",
                  )}
                >
                  {badges[item.path]}
                </TextBlock>
              )}
            </MenuLink>
          </Fragment>
        );
      })}
    </nav>
  );
}
