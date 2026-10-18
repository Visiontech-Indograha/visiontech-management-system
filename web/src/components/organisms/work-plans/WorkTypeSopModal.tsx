import { ActionButton } from "@/components/molecules/ActionButton";
import { Modal, ModalContent, ModalFooter, ModalHeader, ModalTitle } from "@/components/molecules/Modal";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { useImageRequirements } from "@/services/workPlanService";

/**
 * Modal Standarisasi SOP Pengisian Laporan Foto Lapangan (image_requirement).
 * Menampilkan checklist titik wajib difoto, deskripsi panduan, dan foto contoh SOP.
 */
export function WorkTypeSopModal({
  workTypeId,
  workTypeName,
  onClose,
}: {
  workTypeId: string;
  workTypeName: string;
  onClose: () => void;
}) {
  const query = useImageRequirements(workTypeId);

  return (
    <Modal open onOpenChange={(v) => !v && onClose()}>
      <ModalContent className="flex max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-3xl flex-col">
        <ModalHeader>
          <ModalTitle className="text-lg font-semibold text-lens">
            Standarisasi SOP Foto: {workTypeName}
          </ModalTitle>
          <TextBlock className="text-sm text-mist">
            Panduan dokumentasi foto wajib saat survei dan instalasi lapangan sesuai standar divisi.
          </TextBlock>
        </ModalHeader>

        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {query.isPending && <LoadingBar className="h-40 w-full" />}
          {query.isError && (
            <TextBlock className="p-4 text-sm text-danger">
              Gagal memuat standar SOP foto pekerjaan.
            </TextBlock>
          )}

          {query.data && query.data.length === 0 && (
            <div className="rounded-panel border border-dashed border-line p-8 text-center">
              <TextBlock className="text-mist">
                Belum ada item foto standar yang dikonfigurasikan untuk tipe pekerjaan ini.
              </TextBlock>
            </div>
          )}

          {query.data && query.data.length > 0 && (
            <ListBlock className="grid gap-4 sm:grid-cols-2">
              {query.data.map((req) => (
                <ListEntry key={req.image_requirement_id}>
                  <div className="flex h-full flex-col overflow-hidden rounded-panel border border-line bg-surface shadow-card">
                    {/* Image Preview */}
                    <div className="relative aspect-video w-full overflow-hidden bg-canvas">
                      <ImageView
                        src={req.path_image}
                        alt={req.name}
                        className="h-full w-full object-cover transition-transform hover:scale-105"
                      />
                      <TextBlock
                        as="span"
                        className={`absolute right-2 top-2 rounded px-2 py-0.5 text-xs font-semibold ${
                          req.is_mandatory
                            ? "bg-rose-500 text-white"
                            : "bg-slate-600 text-slate-200"
                        }`}
                      >
                        {req.is_mandatory ? "Wajib" : "Opsional"}
                      </TextBlock>
                    </div>

                    {/* Content */}
                    <div className="flex flex-1 flex-col p-3">
                      <TextBlock as="h4" className="font-medium text-lens">
                        {req.name}
                      </TextBlock>
                      {req.description ? (
                        <TextBlock className="mt-1 text-sm text-mist">
                          {req.description}
                        </TextBlock>
                      ) : (
                        <TextBlock className="mt-1 text-xs italic text-mist">
                          (Tidak ada deskripsi tambahan)
                        </TextBlock>
                      )}
                    </div>
                  </div>
                </ListEntry>
              ))}
            </ListBlock>
          )}
        </div>

        <ModalFooter className="border-t border-line pt-3">
          <ActionButton variant="outline" onClick={onClose}>
            Tutup
          </ActionButton>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
