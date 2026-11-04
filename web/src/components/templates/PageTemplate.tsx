import type { ReactNode } from "react";
import { PageHeader } from "../organisms/PageHeader";
import { WorkspaceTabs } from "../organisms/WorkspaceTabs";

/**
 * Kerangka halaman standar (docs/33 §2.1): sub-tab ruang kerja + judul + keterangan + aksi di atas, isi halaman di bawah.
 * Page memakai template ini; template hanya menyusun organism (`WorkspaceTabs`, `PageHeader`).
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
      <WorkspaceTabs />
      <PageHeader title={title} description={description} action={action} />
      {children}
    </>
  );
}
