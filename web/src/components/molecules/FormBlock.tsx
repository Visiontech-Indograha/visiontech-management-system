import { forwardRef, type ComponentProps } from "react";
import { NativeForm, NativeInput, NativeLabel } from "../atoms/NativeControls";
import { Select, SelectOption } from "../atoms/Select";
import { Textarea } from "../atoms/Textarea";

/** Formulir dan kontrol isian tanpa label bawaan untuk organism (label/galat diatur organism atau `Field`). */
export function FormBlock(props: ComponentProps<typeof NativeForm>) {
  return <NativeForm {...props} />;
}
export function ControlLabel(props: ComponentProps<typeof NativeLabel>) {
  return <NativeLabel {...props} />;
}
export const ControlInput = forwardRef<HTMLInputElement, ComponentProps<typeof NativeInput>>(function ControlInput(props, ref) {
  return <NativeInput ref={ref} {...props} />;
});
export const ControlSelect = forwardRef<HTMLSelectElement, ComponentProps<typeof Select>>(function ControlSelect(props, ref) {
  return <Select ref={ref} {...props} />;
});
export function ControlOption(props: ComponentProps<typeof SelectOption>) {
  return <SelectOption {...props} />;
}
export const ControlTextarea = forwardRef<HTMLTextAreaElement, ComponentProps<typeof Textarea>>(function ControlTextarea(props, ref) {
  return <Textarea ref={ref} {...props} />;
});
