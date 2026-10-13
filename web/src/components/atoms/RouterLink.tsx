/**
 * Atom tautan (docs/33 §2.1): satu-satunya pintu ke `Link`/`NavLink` react-router dan `<a>` untuk komponen di atas atom.
 */
import type { AnchorHTMLAttributes } from "react";

export { Link, NavLink } from "react-router-dom";

/** Tautan biasa (`<a>`), mis. unduhan atau alamat luar. */
export function Anchor(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a {...props} />;
}
