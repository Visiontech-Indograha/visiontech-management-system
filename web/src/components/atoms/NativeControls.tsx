import { forwardRef, type FormHTMLAttributes, type InputHTMLAttributes, type LabelHTMLAttributes } from "react";
import { handleInvalid, clearCustomValidity } from "@/lib/nativeValidity";

/** Atom input native tanpa gaya bawaan (mis. kotak centang, berkas); input teks bergaya memakai atom `Input`. */
export const NativeInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function NativeInput({ onInvalid, onInput, ...props }, ref) {
  return <input ref={ref} onInvalid={(e) => { handleInvalid(e); onInvalid?.(e); }} onInput={(e) => { clearCustomValidity(e); onInput?.(e); }} {...props} />;
});

/** Atom label native (`<label>`). */
export function NativeLabel(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} />;
}

/** Atom formulir native (`<form>`). */
export function NativeForm(props: FormHTMLAttributes<HTMLFormElement>) {
  return <form {...props} />;
}

/** Atom gaya global kecil (mis. `@page` untuk cetak). */
export function InlineStyle({ css }: { css: string }) {
  return <style>{css}</style>;
}
