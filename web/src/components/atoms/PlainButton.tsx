import { forwardRef, type ButtonHTMLAttributes } from "react";

/**
 * Atom tombol tanpa gaya bawaan (`<button type="button">`), untuk tombol yang tampilannya ditentukan sendiri
 * (tautan-tombol, tab, ubin). Tombol aksi biasa memakai atom `Button`.
 */
export const PlainButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(function PlainButton(
  { type = "button", ...props },
  ref,
) {
  return <button ref={ref} type={type} {...props} />;
});
