import type { ComponentProps } from "react";
import { Anchor, Link, NavLink } from "../atoms/RouterLink";

/** Tautan antarhalaman (react-router `Link`). */
export function InlineLink(props: ComponentProps<typeof Link>) {
  return <Link {...props} />;
}

/** Tautan menu yang tahu rute aktif (react-router `NavLink`). */
export function MenuLink(props: ComponentProps<typeof NavLink>) {
  return <NavLink {...props} />;
}

/** Tautan biasa / unduhan (`<a>`). */
export function ExternalLink(props: ComponentProps<typeof Anchor>) {
  return <Anchor {...props} />;
}
