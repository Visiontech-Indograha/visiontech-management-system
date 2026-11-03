import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Label } from "../atoms/Label";
import { Input } from "../atoms/Input";
import { Select } from "../atoms/Select";
import { Text } from "../atoms/Text";
import { Textarea } from "../atoms/Textarea";
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
      <Label htmlFor={id} className="text-sm font-medium text-ink">{label}</Label>
      {children(id, error || hint ? msgId : undefined)}
      {error ? (
        <Text id={msgId} role="alert" className="text-sm font-medium text-destructive">
          {error}
        </Text>
      ) : hint ? (
        <Text id={msgId} className="text-xs text-muted-foreground">
          {hint}
        </Text>
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
          className={cn("bg-surface", error && "border-destructive focus-visible:ring-destructive", className)}
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
        <Select
          id={id}
          ref={ref}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={cn(
            "flex h-11 w-full rounded-md border border-input bg-surface px-3 py-1.5 text-base shadow-xs transition-[color,box-shadow] focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
            error && "border-destructive focus-visible:ring-destructive",
            className,
          )}
          {...props}
        >
          {children}
        </Select>
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
        <Textarea
          id={id}
          ref={ref}
          rows={3}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={cn(
            "flex w-full rounded-md border border-input bg-surface px-3 py-2 text-base shadow-xs transition-[color,box-shadow] focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
            error && "border-destructive focus-visible:ring-destructive",
            className,
          )}
          {...props}
        />
      )}
    </FieldShell>
  );
});
