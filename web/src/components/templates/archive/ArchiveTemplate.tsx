import { ArchivePanel } from "@/components/organisms/archive/ArchivePanel";
import { PageTemplate } from "@/components/templates/PageTemplate";

export function ArchiveTemplate() {
  return (
    <PageTemplate title="Arsip" description="Kembalikan data yang pernah dihapus, seperti peralatan, kendaraan, klien, divisi, jabatan, dan mess.">
      <ArchivePanel />
    </PageTemplate>
  );
}
