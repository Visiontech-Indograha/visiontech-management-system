import type { UseQueryResult } from "@tanstack/react-query";
import { Button } from "@/components/atoms/Button";
import { Skeleton } from "@/components/atoms/Skeleton";
import type { WorkType } from "@/services/workTypeService";
import { WorkTypeAddButton } from "./WorkTypeAddButton";

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
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}
      {types.isError && (
        <div role="alert" className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <p className="mb-3 text-danger">Jenis pekerjaan tidak dapat dimuat.</p>
          <Button variant="outline" onClick={() => types.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {types.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-6 text-center shadow-card">
          <p className="mb-3 text-mist">Belum ada jenis pekerjaan. Tambahkan jenis beserta template foto laporannya.</p>
          <WorkTypeAddButton onAdd={onAdd} />
        </div>
      )}
      {types.data && types.data.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {types.data.map((t) => (
            <li key={t.id} className="rounded-panel border border-line bg-surface p-4 shadow-card">
              <div className="mb-2 flex items-start justify-between gap-2">
                <p className="font-medium">{t.name}</p>
                {!t.is_active && <span className="rounded-control bg-hover px-2 py-0.5 text-xs text-mist">Nonaktif</span>}
              </div>
              {t.photos.length === 0 ? (
                <p className="text-sm text-mist">Tanpa template foto.</p>
              ) : (
                <ol className="list-decimal space-y-0.5 pl-5 text-sm">
                  {t.photos.map((p) => (
                    <li key={p.id}>
                      {p.label}
                      {p.required && <span className="ml-1 text-xs text-danger">wajib</span>}
                      {p.example_file_id && <span className="ml-1 text-xs text-mist">· ada foto contoh</span>}
                      {p.hint && <span className="block text-xs text-mist">{p.hint}</span>}
                    </li>
                  ))}
                </ol>
              )}
              <div className="mt-3 flex gap-2">
                <Button variant="outline" size="sm" onClick={() => onEdit(t)}>
                  Ubah
                </Button>
                {t.is_active && (
                  <Button variant="ghost" size="sm" onClick={() => onDeactivate(t)} aria-label={`Nonaktifkan ${t.name}`}>
                    Nonaktifkan
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
