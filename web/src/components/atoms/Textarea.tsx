import { forwardRef, type TextareaHTMLAttributes } from "react";
import { handleInvalid, clearCustomValidity } from "@/lib/nativeValidity";

/** Atom isian teks panjang native (`<textarea>`); gaya diberikan pemanggil lewat `className`. */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ onInvalid, onInput, ...props }, ref) {
  return <textarea ref={ref} onInvalid={(e) => { handleInvalid(e); onInvalid?.(e); }} onInput={(e) => { clearCustomValidity(e); onInput?.(e); }} {...props} />;
});
