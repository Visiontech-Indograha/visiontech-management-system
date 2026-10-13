import { forwardRef, type SelectHTMLAttributes } from "react";

/** Atom pilihan native (`<select>`); gaya diberikan pemanggil lewat `className`. Opsi memakai `<option>` biasa. */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(props, ref) {
  return <select ref={ref} {...props} />;
});

/** Atom opsi untuk `Select`. */
export function SelectOption(props: React.OptionHTMLAttributes<HTMLOptionElement>) {
  return <option {...props} />;
}
