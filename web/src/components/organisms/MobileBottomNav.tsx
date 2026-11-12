import clsx from "clsx";
import { Menu } from "@/components/molecules/Glyphs";
import { MenuLink } from "@/components/molecules/Links";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";
import { MOBILE_PRIMARY_PATHS, type NavItem } from "@/app/navigation";

/**
 * Bilah navigasi bawah khusus ponsel (< 768 px): 4 tujuan utama + tombol laci "Lainnya"
 * agar jempol pengguna langsung menjangkau menu harian tanpa perlu naik ke pojok kiri atas.
 */
export function MobileBottomNav({
  items,
  badges = {},
  onOpenDrawer,
}: {
  items: NavItem[];
  badges?: Record<string, number>;
  onOpenDrawer: () => void;
}) {
  const primaryItems = MOBILE_PRIMARY_PATHS.map((p) => items.find((it) => it.path === p)).filter(
    (it): it is NavItem => Boolean(it),
  );
  const primaryPathSet = new Set<string>(primaryItems.map((it) => it.path));
  const otherBadgeCount = Object.entries(badges).reduce(
    (sum, [path, count]) => (primaryPathSet.has(path) ? sum : sum + (count ?? 0)),
    0,
  );

  return (
    <nav
      aria-label="Navigasi bawah ponsel"
      className="fixed inset-x-0 bottom-0 z-30 flex items-center justify-around border-t border-line bg-surface/95 px-1 pt-1 pb-safe backdrop-blur-sm md:hidden"
    >
      {primaryItems.map((item) => {
        const Icon = item.icon;
        const badge = badges[item.path] ?? 0;
        return (
          <MenuLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              clsx(
                "relative flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-control px-1 py-1 text-xs font-medium transition-colors",
                isActive ? "text-primary font-semibold" : "text-mist hover:text-ink",
              )
            }
          >
            <Icon size={20} strokeWidth={1.9} aria-hidden />
            <TextBlock as="span" className="max-w-full truncate">
              {item.label}
            </TextBlock>
            {badge > 0 && (
              <TextBlock
                as="span"
                aria-label={`${badge} menunggu`}
                className="absolute right-3 top-1 rounded-full bg-gold px-1.5 text-xs font-bold leading-4 text-ink"
              >
                {badge}
              </TextBlock>
            )}
          </MenuLink>
        );
      })}
      <PlainAction
        type="button"
        onClick={onOpenDrawer}
        aria-label="Menu lainnya"
        className="relative flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-control px-1 py-1 text-xs font-medium text-mist hover:text-ink"
      >
        <Menu size={20} strokeWidth={1.9} aria-hidden />
        <TextBlock as="span" className="max-w-full truncate">
          Menu
        </TextBlock>
        {otherBadgeCount > 0 && (
          <TextBlock
            as="span"
            aria-label={`${otherBadgeCount} menunggu di menu lain`}
            className="absolute right-3 top-1 rounded-full bg-gold px-1.5 text-xs font-bold leading-4 text-ink"
          >
            {otherBadgeCount}
          </TextBlock>
        )}
      </PlainAction>
    </nav>
  );
}
