import type { ComponentProps } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "../atoms/Avatar";

/** Avatar untuk organism (foto profil, inisial pengguna). */
export function AvatarBlock(props: ComponentProps<typeof Avatar>) {
  return <Avatar {...props} />;
}

export function AvatarBlockImage(props: ComponentProps<typeof AvatarImage>) {
  return <AvatarImage {...props} />;
}

export function AvatarBlockFallback(props: ComponentProps<typeof AvatarFallback>) {
  return <AvatarFallback {...props} />;
}
