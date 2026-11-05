import clsx from "clsx";
import { useState } from "react";
import { LogOut, ShieldCheck } from "@/components/molecules/Glyphs";
import { MenuLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { PlainAction } from "@/components/molecules/PlainAction";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { UserAvatar } from "@/components/organisms/UserAvatar";

/** Kartu pengguna di dasar rail kiri + tautan "Akun & keamanan" + tombol keluar. */
export function SidebarProfile({ email, name, photoFileId, roleLabel, scopeLines = [], collapsed, onLogout }: {
  scopeLines?: string[];
  email: string;
  name?: string | null;
  photoFileId?: string | null;
  roleLabel: string;
  collapsed: boolean;
  onLogout: () => void;
}) {
  const [confirmLogout, setConfirmLogout] = useState(false);
  return (
    <div className="p-3">
      <div className={clsx("flex items-center gap-3 rounded-panel bg-surface p-2.5 shadow-card ring-1 ring-line", collapsed && "md:justify-center md:p-1.5")}>
        <UserAvatar name={name || email.split("@")[0]} fileId={photoFileId} />
        <div className={clsx("min-w-0 flex-1", collapsed && "md:sr-only")}>
          <TextBlock className="truncate text-sm font-semibold text-ink">{name || email}</TextBlock>
          <TextBlock className="text-xs text-mist">{roleLabel}</TextBlock>
          {scopeLines.map((l) => (
            <TextBlock key={l} className="text-xs text-mist">{l}</TextBlock>
          ))}
        </div>
      </div>
      <MenuLink
        to="/account"
        className="mt-2 flex h-10 w-full items-center gap-3 rounded-control px-3 text-sm text-mist transition-colors hover:bg-hover hover:text-ink"
      >
        <ShieldCheck size={19} strokeWidth={1.75} aria-hidden />
        <TextBlock as="span" className={clsx(collapsed && "md:sr-only")}>Akun & keamanan</TextBlock>
      </MenuLink>
      <PlainAction
        type="button"
        onClick={() => setConfirmLogout(true)}
        className="flex h-10 w-full items-center gap-3 rounded-control px-3 text-sm text-mist transition-colors hover:bg-danger-bg hover:text-danger"
      >
        <LogOut size={19} strokeWidth={1.75} aria-hidden />
        <TextBlock as="span" className={clsx(collapsed && "md:sr-only")}>Keluar</TextBlock>
      </PlainAction>
      <ConfirmDialog
        open={confirmLogout}
        title="Keluar dari akun?"
        message="Anda akan keluar dari aplikasi di perangkat ini."
        confirmLabel="Keluar"
        onConfirm={onLogout}
        onClose={() => setConfirmLogout(false)}
      />
    </div>
  );
}
