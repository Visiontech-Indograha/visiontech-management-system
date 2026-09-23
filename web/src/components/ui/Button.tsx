import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-lens text-white hover:bg-lens-hover border border-transparent",
  secondary: "bg-surface text-ink border border-line hover:bg-hover",
  ghost: "bg-transparent text-ink border border-transparent hover:bg-hover",
  danger: "bg-surface text-danger border border-danger hover:bg-danger-soft",
};

export function Button({
  variant = "primary",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={clsx(
        "inline-flex h-10 items-center justify-center gap-2 rounded-control px-4 text-sm font-semibold",
        "transition-colors duration-[var(--motion-fast)] ease-out disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
