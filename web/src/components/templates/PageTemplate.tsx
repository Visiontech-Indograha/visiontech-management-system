import type { ReactNode } from "react";
import { PageHeader } from "../organisms/PageHeader";

/**
 * Kerangka halaman standar (docs/33 §2.1): judul + keterangan + aksi di atas, isi halaman di bawah.
 * Page memakai template ini; template hanya menyusun organism (`PageHeader`).
 *
 *   <PageTemplate title="Lokasi kerja" description="…" action={<SiteActions … />}>
 *     <SiteTable … />
 *   </PageTemplate>
 */
export function PageTemplate({ title, description, action, children }: {
  title: string;
  description?: ReactNode;
  /** Aksi utama di kanan judul — berupa organism. */
  action?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <>
      <PageHeader title={title} description={description} action={action} />
      {children}
    </>
  );
}
