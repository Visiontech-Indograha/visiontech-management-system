import { forwardRef, type TextareaHTMLAttributes } from "react";

/** Atom isian teks panjang native (`<textarea>`); gaya diberikan pemanggil lewat `className`. */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(props, ref) {
  return <textarea ref={ref} {...props} />;
});
