import type { ComponentProps } from "react";
import { Fieldset, FieldsetLegend } from "../atoms/Fieldset";

/** Kelompok isian berjudul untuk organism: <FieldGroup><FieldGroupLegend>…</FieldGroupLegend>…</FieldGroup> */
export function FieldGroup(props: ComponentProps<typeof Fieldset>) {
  return <Fieldset {...props} />;
}
export function FieldGroupLegend(props: ComponentProps<typeof FieldsetLegend>) {
  return <FieldsetLegend {...props} />;
}
