import logo from "@/assets/brand/logo-visiontech.png";
import { NotificationBell } from "./NotificationBell";
import { Menu } from "@/components/molecules/Glyphs";
import { PlainAction } from "@/components/molecules/PlainAction";
import { ImageView } from "@/components/molecules/ImageView";

/** Bilah atas khusus ponsel (< 768 px): tombol buka laci menu, logo, lonceng notifikasi. */
export function MobileTopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center border-b border-line bg-surface/90 px-4 backdrop-blur-sm md:hidden">
      <PlainAction
        type="button"
        className="rounded-control p-2 text-ink hover:bg-hover"
        onClick={onOpenMenu}
        aria-label="Buka menu"
      >
        <Menu size={20} />
      </PlainAction>
      <ImageView src={logo} alt="Visiontech Indograha" className="ml-2 h-7 w-auto object-contain" />
      <NotificationBell className="ml-auto" />
    </header>
  );
}
