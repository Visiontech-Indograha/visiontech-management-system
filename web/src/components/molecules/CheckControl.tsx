import type { ComponentProps } from "react";
import { Checkbox } from "../atoms/Checkbox";

/** Kotak centang bergaya (shadcn Checkbox). */
export function CheckControl(props: ComponentProps<typeof Checkbox>) {
  return <Checkbox {...props} />;
}
