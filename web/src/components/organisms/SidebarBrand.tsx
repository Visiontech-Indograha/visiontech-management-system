import clsx from "clsx";
import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import logo from "@/assets/brand/logo-visiontech.png";

/** Kepala rail kiri: logo, tombol ciutkan/perluas (desktop), dan tombol tutup laci (ponsel). */
export function SidebarBrand({ collapsed, onToggleCollapse, onClose }: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onClose: () => void;
}) {
  return (
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
        onClick={onToggleCollapse}
        aria-label={collapsed ? "Perluas menu" : "Ciutkan menu"}
      >
        {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
      </button>
      <button
        type="button"
        className="rounded-control p-1 text-mist hover:bg-hover md:hidden"
        onClick={onClose}
        aria-label="Tutup menu"
      >
        <X size={20} />
      </button>
    </div>
  );
}
