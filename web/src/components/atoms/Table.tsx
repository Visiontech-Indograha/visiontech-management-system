import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

/** Atom tabel HTML (tanpa gaya bawaan; gaya lewat `className`). Disusun molecule `TableBlock`. */
export function Table(props: HTMLAttributes<HTMLTableElement>) {
  return <table {...props} />;
}
export function TableHead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}
export function TableBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}
export function TableRow(props: HTMLAttributes<HTMLTableRowElement>) {
  return <tr {...props} />;
}
export function TableHeaderCell(props: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th {...props} />;
}
export function TableCell(props: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td {...props} />;
}
