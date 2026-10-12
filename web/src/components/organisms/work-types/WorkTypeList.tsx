import type { UseQueryResult } from "@tanstack/react-query";
import type { WorkType } from "@/services/workTypeService";
import { WorkTypeAddButton } from "./WorkTypeAddButton";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";

/** Kartu jenis pekerjaan + slot fotonya; keadaan memuat, galat (+ coba lagi), kosong (+ tambah), berhasil. */
export function WorkTypeList({ types, onAdd, onEdit, onDeactivate }: {
  types: UseQueryResult<WorkType[]>;
  onAdd: () => void;
  onEdit: (type: WorkType) => void;
  onDeactivate: (type: WorkType) => void;
}) {
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
      {types.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <TextBlock className="mb-3 text-mist">Belum ada jenis pekerjaan. Tambahkan jenis beserta template foto laporannya.</TextBlock>
          <WorkTypeAddButton onAdd={onAdd} />
        </div>
      )}
      {types.data && types.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {types.data.map((t) => (
            <ListEntry key={t.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="mb-2 flex items-start justify-between gap-2">
                <TextBlock className="font-medium">{t.name}</TextBlock>
                {!t.is_active && <TextBlock as="span" className="rounded-control bg-hover px-2 py-0.5 text-xs text-mist">Nonaktif</TextBlock>}
              </div>
              {t.photos.length === 0 ? (
                <TextBlock className="text-sm text-mist">Tanpa template foto.</TextBlock>
              ) : (
                <ListBlock as="ol" className="list-decimal space-y-0.5 pl-5 text-sm">
                  {t.photos.map((p) => (
                    <ListEntry key={p.id}>
                      {p.label}
                      {p.required && <TextBlock as="span" className="ml-1 text-xs text-danger">wajib</TextBlock>}
                      {p.example_file_id && <TextBlock as="span" className="ml-1 text-xs text-mist">· ada foto contoh</TextBlock>}
                      {p.hint && <TextBlock as="span" className="block text-xs text-mist">{p.hint}</TextBlock>}
                    </ListEntry>
                  ))}
                </ListBlock>
              )}
              <div className="mt-3 flex gap-2">
                <ActionButton variant="outline" size="sm" onClick={() => onEdit(t)}>
                  Ubah
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
      )}
    </>
  );
}
