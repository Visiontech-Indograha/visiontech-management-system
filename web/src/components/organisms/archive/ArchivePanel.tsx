import { useState } from "react";
import { SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ArchiveList } from "@/components/organisms/archive/ArchiveList";
import { ARCHIVE_MODULES } from "@/services/archiveService";
import { useSession } from "@/stores/sessionStore";

/** Isi halaman Arsip: pilih jenis data (hanya yang boleh dipulihkan akun ini), lalu daftar item terhapus. */
export function ArchivePanel() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const modules = ARCHIVE_MODULES.filter((m) => perms.includes(m.permission));
  const [slug, setSlug] = useState("");
  const current = modules.find((m) => m.slug === slug) ?? modules[0];
  if (!current) {
    return <TextBlock role="alert" className="text-sm text-mist">Akun Anda belum boleh memulihkan data apa pun.</TextBlock>;
  }
  return (
    <div className="space-y-4">
      <SelectField label="Jenis data" value={current.slug} onChange={(e) => setSlug(e.target.value)}>
        {modules.map((m) => <ControlOption key={m.slug} value={m.slug}>{m.label}</ControlOption>)}
      </SelectField>
      <ArchiveList key={current.slug} slug={current.slug} label={current.label} codeLabel={current.codeLabel} />
    </div>
  );
}
