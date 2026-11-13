import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { Input } from "../atoms/Input";
import { Label } from "../atoms/Label";
import { Text } from "../atoms/Text";

const FILE_INPUT = "file";

/** Kolom unggah berkas dengan label, bantuan, dan galat; satu-satunya tempat input berkas baru (aturan R5). */
export const UploadField = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; error?: string; hint?: string }
>(function UploadField({ label, error, hint, ...props }, ref) {
  const id = useId();
  const msgId = `${id}-msg`;
  const note = error ?? hint;
  return (
    <div className="mb-4 space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium text-ink">{label}</Label>
      <Input id={id} ref={ref} aria-invalid={!!error} aria-describedby={note ? msgId : undefined} {...props} type={FILE_INPUT} />
      {note && <Text id={msgId} role={error ? "alert" : undefined} className={error ? "text-sm font-medium text-destructive" : "text-xs text-muted-foreground"}>{note}</Text>}
    </div>
  );
});
