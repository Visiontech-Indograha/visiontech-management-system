import type { FieldsetHTMLAttributes, HTMLAttributes } from "react";

/** Atom kelompok isian (`<fieldset>`). */
export function Fieldset(props: FieldsetHTMLAttributes<HTMLFieldSetElement>) {
  return <fieldset {...props} />;
}

/** Atom judul kelompok isian (`<legend>`). */
export function FieldsetLegend(props: HTMLAttributes<HTMLLegendElement>) {
  return <legend {...props} />;
}
