import { forwardRef, type SelectHTMLAttributes } from "react";
import { handleInvalid, clearCustomValidity } from "@/lib/nativeValidity";

/** Atom pilihan native (`<select>`); gaya diberikan pemanggil lewat `className`. Opsi memakai `<option>` biasa. */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ onInvalid, onChange, ...props }, ref) {
  return <select ref={ref} onInvalid={(e) => { handleInvalid(e); onInvalid?.(e); }} onChange={(e) => { clearCustomValidity(e); onChange?.(e); }} {...props} />;
});

/** Atom opsi untuk `Select`. */
export function SelectOption(props: React.OptionHTMLAttributes<HTMLOptionElement>) {
  return <option {...props} />;
}
