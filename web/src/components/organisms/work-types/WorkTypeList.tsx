import { ListPagination } from "@/components/organisms/ListPagination";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { pagedView, type ListControls } from "@/hooks/usePagedList";
import type { Paged } from "@/lib/paged";
import { useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { WORK_TYPE_KIND_LABEL, type WorkType } from "@/services/workTypeService";
import { WorkTypeAddButton } from "./WorkTypeAddButton";
import { WorkTypeMaterialsDialog } from "./WorkTypeMaterialsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { ExternalLink } from "@/components/molecules/Links";
import { useFileUrl } from "@/hooks/useFileUrl";

/** Foto panduan pengambilan gambar dari PM (klik → ukuran penuh di tab baru). */
function ExamplePhoto({ fileId, label }: { fileId: string; label: string }) {
  const { data: url } = useFileUrl(fileId, "view");
  return (
    <div className="mt-1 h-24 w-32 overflow-hidden rounded-control border border-line bg-hover">
      {url && (
        <ExternalLink href={url} target="_blank" rel="noopener">
          <ImageView src={url} alt={`Contoh ${label}`} className="h-full w-full object-cover" />
        </ExternalLink>
      )}
    </div>
  );
}

/** Kartu jenis pekerjaan + slot fotonya; keadaan memuat, galat (+ coba lagi), kosong (+ tambah), berhasil. */
export function WorkTypeList({ controls, types, onAdd, onEdit, onDeactivate }: {
  controls: ListControls;
  types: UseQueryResult<Paged<WorkType>>;
  onAdd: () => void;
  onEdit: (type: WorkType) => void;
  onDeactivate: (type: WorkType) => void;
}) {
  const [selectedForMaterials, setSelectedForMaterials] = useState<WorkType | null>(null);
  const view = pagedView(types, controls);
  return (
    <>
      {types.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-24" />
          <LoadingBar className="h-24" />
        </div>
      )}
      {types.isError && (
        <div role="alert" className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="mb-3 text-danger">Jenis pekerjaan tidak dapat dimuat.</TextBlock>
          <ActionButton variant="outline" onClick={() => types.refetch()}>
            Coba lagi
          </ActionButton>
        </div>
      )}
      {types.data && types.data.total === 0 && !view.active && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="mb-3 text-mist">Belum ada jenis pekerjaan. Tambahkan jenis beserta template foto laporannya.</TextBlock>
          <WorkTypeAddButton onAdd={onAdd} />
        </div>
      )}
      {types.data && (types.data.total > 0 || view.active) && (
        <>
        <ListToolbar value={view.input} onChange={view.setInput} placeholder="Cari jenis pekerjaan atau divisi..." active={view.active} onReset={view.reset} />
        {view.total === 0 && <TextBlock className="rounded-panel border border-line bg-surface p-6 text-center text-mist">Tidak ada yang cocok dengan pencarian.</TextBlock>}
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {view.rows.map((t) => (
            <ListEntry key={t.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <TextBlock className="font-medium">{t.name}</TextBlock>
                  {t.division_name && (
                    <TextBlock as="span" className="mt-1 inline-block rounded-control bg-hover px-2 py-0.5 text-xs font-medium text-foreground">
                      {t.division_name}
                    </TextBlock>
                  )}
                  {t.description && (
                    <TextBlock className="mt-1 text-xs text-mist">{t.description}</TextBlock>
                  )}
                </div>
                {t.kind !== "WORK" && (
                  <TextBlock as="span" className="rounded-control bg-lens/10 px-2 py-0.5 text-xs text-lens">
                    {WORK_TYPE_KIND_LABEL[t.kind ?? "WORK"]}
                  </TextBlock>
                )}
                {!t.is_active && <TextBlock as="span" className="rounded-control bg-hover px-2 py-0.5 text-xs text-mist">Nonaktif</TextBlock>}
              </div>
              {t.kind === "SURVEY_POINT" && (
                <TextBlock className="mb-1 text-xs text-mist">
                  {`Pemasangan lanjutan: ${t.follow_up_name ?? "belum ditentukan"}`}
                </TextBlock>
              )}
              {t.photos.length === 0 ? (
                <TextBlock className="text-sm text-mist">Tanpa template foto.</TextBlock>
              ) : (
                <ListBlock as="ol" className="list-decimal space-y-0.5 pl-5 text-sm">
                  {t.photos.map((p) => (
                    <ListEntry key={p.id}>
                      {p.label}
                      {p.required && <TextBlock as="span" className="ml-1 text-xs text-danger">wajib</TextBlock>}
                      {p.hint && <TextBlock as="span" className="block text-xs text-mist">{p.hint}</TextBlock>}
                      {p.example_file_id && <ExamplePhoto fileId={p.example_file_id} label={p.label} />}
                    </ListEntry>
                  ))}
                </ListBlock>
              )}
              <div className="mt-3 flex gap-2">
                <ActionButton variant="outline" size="sm" onClick={() => onEdit(t)}>
                  Ubah
                </ActionButton>
                <ActionButton variant="secondary" size="sm" onClick={() => setSelectedForMaterials(t)}>
                  BoM Standar
                </ActionButton>
                {t.is_active && (
                  <ActionButton variant="ghost" size="sm" onClick={() => onDeactivate(t)} aria-label={`Nonaktifkan ${t.name}`}>
                    Nonaktifkan
                  </ActionButton>
                )}
              </div>
            </ListEntry>
          ))}
        </ListBlock>
        {view.total > 0 && <ListPagination total={view.total} noun="jenis" page={view.shownPage} shownPage={view.shownPage} lastPage={view.lastPage} onPageChange={view.setPage} />}
        </>
      )}

      <WorkTypeMaterialsDialog
        workType={selectedForMaterials}
        onClose={() => setSelectedForMaterials(null)}
      />
    </>
  );
}
