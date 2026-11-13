import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FilePreview } from "@/components/molecules/FilePreview";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { QueryState } from "@/components/molecules/QueryState";
import { TextBlock } from "@/components/molecules/TextBlock";
import { UploadField } from "@/components/molecules/UploadField";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import {
  attachmentErrorText, MAX_ATTACHMENTS, useAddAttachment, useAttachments, useRemoveAttachment,
  type Attachment, type AttachmentKind,
} from "@/services/attachmentService";

const sizeText = (b: number) => (b >= 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

function AttachmentRow({ item: a, canRemove, onRemove }: { item: Attachment; canRemove: boolean; onRemove: () => void }) {
  return (
    <ListEntry className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-line bg-surface p-3">
      <div className="min-w-0">
        <TextBlock className="truncate text-sm font-medium">{a.file_name}</TextBlock>
        <TextBlock className="text-xs text-mist">{sizeText(a.byte_size)}</TextBlock>
      </div>
      <div className="flex items-center gap-2">
        <FilePreview fileId={a.file_id} fileName={a.file_name} />
        {canRemove && (
          <ActionButton variant="outline" size="sm" aria-label={`Hapus ${a.file_name}`} onClick={onRemove}>
            Hapus
          </ActionButton>
        )}
      </div>
    </ListEntry>
  );
}

/** Daftar lampiran satu pengajuan (lembur atau mess): lihat, tambah, hapus. `locked` = pengajuan sudah diputuskan/dibatalkan. */
export function AttachmentPanel({ kind, parentId, locked = false }: { kind: AttachmentKind; parentId: string; locked?: boolean }) {
  const query = useAttachments(kind, parentId);
  const add = useAddAttachment(kind, parentId);
  const remove = useRemoveAttachment(kind, parentId);
  const [removing, setRemoving] = useState<Attachment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [serverLocked, setServerLocked] = useState(false);
  const rows = query.data ?? [];
  const uploading = add.isPending;
  const isLocked = locked || serverLocked;

  const fail = (err: unknown) => {
    if (err instanceof ApiError && err.code === "LAMPIRAN_TERKUNCI") setServerLocked(true);
    setError(attachmentErrorText(err) ?? errorMessage(err));
  };

  const onPick = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    try {
      await add.mutateAsync(file);
      toast.success("Lampiran ditambahkan.");
    } catch (err) {
      fail(err);
    }
  };

  const confirmRemove = async () => {
    if (!removing) return;
    try {
      await remove.mutateAsync(removing.file_id);
      toast.success("Lampiran dihapus.");
    } catch (err) {
      fail(err);
    }
    setRemoving(null);
  };

  return (
    <section className="space-y-3" aria-label="Lampiran">
      <QueryState query={query} errorText="Lampiran tidak dapat dimuat." empty={rows.length === 0} emptyText="Belum ada lampiran.">
        <ListBlock className="space-y-2">
          {rows.map((a) => (
            <AttachmentRow key={a.file_id} item={a} canRemove={!isLocked && a.mine} onRemove={() => setRemoving(a)} />
          ))}
        </ListBlock>
      </QueryState>
      {isLocked ? (
        <TextBlock className="text-sm text-mist">Pengajuan ini sudah diputuskan atau dibatalkan, jadi lampiran tidak bisa diubah lagi.</TextBlock>
      ) : rows.length >= MAX_ATTACHMENTS ? (
        <TextBlock className="text-sm text-mist">Lampiran sudah penuh (paling banyak {MAX_ATTACHMENTS} berkas).</TextBlock>
      ) : (
        <UploadField
          label="Tambah lampiran"
          accept=".jpg,.jpeg,.png,.pdf"
          hint="JPG, PNG, atau PDF, paling besar 10 MB."
          disabled={uploading}
          onChange={(e) => {
            const input = e.currentTarget;
            void onPick(input.files?.[0]).then(() => {
              input.value = "";
            });
          }}
        />
      )}
      {uploading && <TextBlock className="text-sm text-mist" role="status">Mengunggah…</TextBlock>}
      {error && <TextBlock role="alert" className="text-sm font-medium text-danger">{error}</TextBlock>}
      <ConfirmDialog
        open={removing !== null}
        title="Hapus lampiran?"
        message={removing ? `${removing.file_name} akan dihapus dari pengajuan ini.` : ""}
        confirmLabel="Hapus"
        danger
        busy={remove.isPending}
        onConfirm={() => void confirmRemove()}
        onClose={() => setRemoving(null)}
      />
    </section>
  );
}
