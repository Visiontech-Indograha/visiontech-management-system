import clsx from "clsx";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

const CONTROL =
  "h-10 w-full rounded-control border border-line bg-surface px-3 text-sm text-ink placeholder:text-mist";

interface FieldShellProps {
  label: string;
  error?: string;
  hint?: string;
  children: (id: string, describedBy: string | undefined) => ReactNode;
}

/** Label di atas, bantuan di bawah, galat inline (docs/06-UI-UX §3). */
function FieldShell({ label, error, hint, children }: FieldShellProps) {
  const id = useId();
  const msgId = `${id}-msg`;
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1 block text-sm font-medium">
        {label}
      </label>
      {children(id, error || hint ? msgId : undefined)}
      {error ? (
        <p id={msgId} role="alert" className="mt-1 text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={msgId} className="mt-1 text-sm text-mist">
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
        <input
          id={id}
          ref={ref}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={clsx(CONTROL, error && "border-danger", className)}
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
          className={clsx(CONTROL, error && "border-danger", className)}
          {...props}
        >
          {children}
        </select>
      )}
    </FieldShell>
  );
});
