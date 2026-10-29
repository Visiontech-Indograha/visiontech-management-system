import clsx from "clsx";
import { AvatarBlock, AvatarBlockFallback, AvatarBlockImage } from "@/components/molecules/AvatarBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useFileUrl } from "@/hooks/useFileUrl";
import { initialsOf } from "@/lib/initials";

const SIZE = {
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-16 text-lg",
  xl: "size-24 text-2xl",
} as const;

/**
 * Avatar orang: foto profil dari server (id berkas `photo_file_id`) bila ada, selain itu inisial nama.
 * Dipakai di sidebar, direktori, absensi, tim, cuti, mess, dan offboarding agar tampilannya seragam.
 */
export function UserAvatar({
  name,
  fileId,
  size = "md",
  className,
}: {
  name: string | null | undefined;
  fileId?: string | null;
  size?: keyof typeof SIZE;
  className?: string;
}) {
  const { data: src } = useFileUrl(fileId, size === "xl" || size === "lg" ? "view" : "thumb");

  return (
    <AvatarBlock className={clsx("shrink-0 ring-1 ring-line", SIZE[size], className)} aria-label={name ?? "Foto profil"}>
      {src && <AvatarBlockImage src={src} alt={name ?? "Foto profil"} className="object-cover" />}
      <AvatarBlockFallback className="bg-accent font-semibold text-lens">
        <TextBlock as="span">{initialsOf(name)}</TextBlock>
      </AvatarBlockFallback>
    </AvatarBlock>
  );
}
