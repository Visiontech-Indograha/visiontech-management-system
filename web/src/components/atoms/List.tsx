import type { HTMLAttributes, LiHTMLAttributes, OlHTMLAttributes } from "react";

/** Atom daftar: `ul` (bawaan), `ol`, atau `dl` lewat `as`. */
export function List({ as: Tag = "ul", ...props }: OlHTMLAttributes<HTMLElement> & { as?: "ul" | "ol" | "dl" }) {
  return <Tag {...props} />;
}

/** Atom butir daftar (`li`). */
export function ListItem(props: LiHTMLAttributes<HTMLLIElement>) {
  return <li {...props} />;
}

/** Atom pengelompok istilah–nilai di dalam `dl` (`div`). */
export function ListGroup(props: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}
