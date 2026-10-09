import type { ComponentProps } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "../atoms/Table";

/** Tabel data untuk organism: TableBlock > TableBlockHead/TableBlockBody > TableBlockRow > TableBlockHeaderCell/TableBlockCell. */
export function TableBlock(props: ComponentProps<typeof Table>) {
  return <Table {...props} />;
}
export function TableBlockHead(props: ComponentProps<typeof TableHead>) {
  return <TableHead {...props} />;
}
export function TableBlockBody(props: ComponentProps<typeof TableBody>) {
  return <TableBody {...props} />;
}
export function TableBlockRow(props: ComponentProps<typeof TableRow>) {
  return <TableRow {...props} />;
}
export function TableBlockHeaderCell(props: ComponentProps<typeof TableHeaderCell>) {
  return <TableHeaderCell {...props} />;
}
export function TableBlockCell(props: ComponentProps<typeof TableCell>) {
  return <TableCell {...props} />;
}
