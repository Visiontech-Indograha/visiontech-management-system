import type { ComponentProps } from "react";
import { List, ListGroup, ListItem } from "../atoms/List";

/** Daftar (`ul`/`ol`/`dl`) untuk organism. */
export function ListBlock(props: ComponentProps<typeof List>) {
  return <List {...props} />;
}

/** Butir daftar. */
export function ListEntry(props: ComponentProps<typeof ListItem>) {
  return <ListItem {...props} />;
}

/** Pasangan istilah–nilai di dalam daftar `dl`. */
export function ListPair(props: ComponentProps<typeof ListGroup>) {
  return <ListGroup {...props} />;
}
