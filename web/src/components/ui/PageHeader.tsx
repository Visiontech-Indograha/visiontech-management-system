import type { ReactNode } from "react";

/** Judul besar di kiri + keterangan opsional, aksi utama di kanan (R-12: gaya kantor modern). */
export function PageHeader({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 md:mb-8">
      <div className="min-w-0">
        <h1 className="text-title-lg text-ink md:text-display">{title}</h1>
        {description && <p className="mt-1 text-body-sm text-mist">{description}</p>}
      </div>
      {action && <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>}
    </div>
  );
}
