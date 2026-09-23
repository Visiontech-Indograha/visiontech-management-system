import type { ReactNode } from "react";

/** Judul di kiri, aksi utama di kanan, garis tipis di bawah (docs/06-UI-UX §2). */
export function PageHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4 border-b border-line pb-4">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {action}
    </div>
  );
}
