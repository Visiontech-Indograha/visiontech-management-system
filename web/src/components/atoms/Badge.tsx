import clsx from "clsx";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE: Record<Tone, { box: string; dot: string }> = {
  success: { box: "bg-success-bg text-success", dot: "bg-success" },
  warning: { box: "bg-warning-bg text-warning", dot: "bg-warning" },
  danger: { box: "bg-danger-bg text-danger", dot: "bg-danger" },
  info: { box: "bg-info-bg text-info", dot: "bg-info" },
  neutral: { box: "bg-muted text-muted-foreground", dot: "bg-muted-foreground" },
};

/** Titik warna + label: status terbaca tanpa warna (docs/06-UI-UX §1 prinsip 3). */
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-tag px-2 py-0.5 text-xs font-medium",
        TONE[tone].box,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", TONE[tone].dot)} aria-hidden />
      {children}
    </span>
  );
}
