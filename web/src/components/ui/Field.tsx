import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Label } from "./label";
import { Input } from "./input";
import { cn } from "@/lib/utils";

interface FieldShellProps {
  label: string;
  error?: string;
  hint?: string;
  children: (id: string, describedBy: string | undefined) => ReactNode;
}

/** Label di atas, bantuan di bawah, galat inline (docs/06-UI-UX A 3). */
function FieldShell({ label, error, hint, children }: FieldShellProps) {
  const id = useId();
  const msgId = `${id}-msg`;
  return (
    <div className="mb-4 space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children(id, error || hint ? msgId : undefined)}
      {error ? (
        <p id={msgId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={msgId} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export const TextField = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }
>(function TextField({ label, error, hint, className, ...props }, ref) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      {(id, describedBy) => (
        <Input
          id={id}
          ref={ref}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={cn(error && "border-destructive focus-visible:ring-destructive", className)}
          {...props}
        />
      )}
    </FieldShell>
  );
});

export const SelectField = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string; hint?: string }
>(function SelectField({ label, error, hint, className, children, ...props }, ref) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      {(id, describedBy) => (
        <select
          id={id}
          ref={ref}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-destructive focus-visible:ring-destructive",
            className
          )}
          {...props}
        >
          {children}
        </select>
      )}
    </FieldShell>
  );
});


export const TextAreaField = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string; hint?: string }
>(function TextAreaField({ label, error, hint, className, ...props }, ref) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      {(id, describedBy) => (
        <textarea
          id={id}
          ref={ref}
          rows={3}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={cn(
            "flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
            error && "border-destructive focus-visible:ring-destructive",
            className,
          )}
          {...props}
        />
      )}
    </FieldShell>
  );
});
