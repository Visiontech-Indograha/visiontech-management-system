import clsx from "clsx";
import { useState } from "react";
import { LogOut, ShieldCheck } from "@/components/molecules/Glyphs";
import { MenuLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { PlainAction } from "@/components/molecules/PlainAction";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";

function initials(email: string) {
  const name = email.split("@")[0].replace(/[^a-z]/gi, " ").trim();
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? parts[0]?.[1] ?? "")).toUpperCase() || "V";
}

/** Kartu pengguna di dasar rail kiri + tautan "Akun & keamanan" + tombol keluar. */
export function SidebarProfile({ email, roleLabel, collapsed, onLogout }: {
  email: string;
  roleLabel: string;
  collapsed: boolean;
  onLogout: () => void;
}) {
  const [confirmLogout, setConfirmLogout] = useState(false);
  return (
    <div className="p-3">
      <div className={clsx("flex items-center gap-3 rounded-panel bg-surface p-2.5 shadow-card ring-1 ring-line", collapsed && "md:justify-center md:p-1.5")}>
        <TextBlock as="span"
          aria-hidden
          className="grid size-9 shrink-0 place-items-center rounded-full bg-accent text-sm font-semibold text-lens"
        >
          {initials(email)}
        </TextBlock>
        <div className={clsx("min-w-0 flex-1", collapsed && "md:sr-only")}>
          <TextBlock className="truncate text-sm font-semibold text-ink">{email}</TextBlock>
          <TextBlock className="text-xs text-mist">{roleLabel}</TextBlock>
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
