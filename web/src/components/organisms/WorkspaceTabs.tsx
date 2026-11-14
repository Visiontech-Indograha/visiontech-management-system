import clsx from "clsx";
import { useLocation } from "react-router-dom";
import { MenuLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { visibleNav } from "@/app/navigation";
import { useSession } from "@/stores/sessionStore";

const WORKSPACE_CLUSTERS: readonly (readonly string[])[] = [
  ["/work-orders", "/work-plans", "/alokasi-mingguan"],
  ["/attendance", "/attendance-recap", "/overtime", "/overtime-recap", "/leaves"],
  ["/hikvision", "/hikvision/banding"],
  ["/clients", "/teams"],
  ["/directory", "/offboarding"],
];

/**
 * Tab penghubung antar-halaman serumpun (Planning, Kehadiran & Waktu, Pekerjaan Klien, SDM)
 * agar pengguna berpindah halaman dalam 1 ketukan tanpa membuka ulang menu laci/sidebar.
 */
export function WorkspaceTabs() {
  const { pathname } = useLocation();
  const { me } = useSession();
  const allowed = visibleNav(me?.permissions ?? []);
  const cluster = WORKSPACE_CLUSTERS.find((paths) => paths.includes(pathname));
  if (!cluster) return null;

  const tabs = cluster
    .map((p) => allowed.find((it) => it.path === p))
    .filter((it): it is NonNullable<typeof it> => Boolean(it));

  if (tabs.length < 2) return null;

  return (
    <nav
      aria-label="Sub-navigasi ruang kerja"
      className="no-scrollbar -mx-4 mb-4 flex items-center gap-1.5 overflow-x-auto border-b border-line px-4 pb-2.5 md:mx-0 md:px-0"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <MenuLink
            key={tab.path}
            to={tab.path}
            end
            className={({ isActive }) =>
              clsx(
                "inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors",
                isActive
                  ? "border-primary bg-primary text-primary-foreground shadow-xs"
                  : "border-line bg-surface text-foreground hover:border-primary/40 hover:bg-accent hover:text-primary",
              )
            }
          >
            <Icon size={14} strokeWidth={2} aria-hidden />
            <TextBlock as="span">{tab.label}</TextBlock>
          </MenuLink>
        );
      })}
    </nav>
  );
}
