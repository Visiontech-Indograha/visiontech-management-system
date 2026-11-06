import { useRef, useState, type ChangeEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ControlInput } from "@/components/molecules/FormBlock";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { errorMessage } from "@/lib/errors";
import { fetchMe } from "@/services/authService";
import { useChangeMyPhoto } from "@/services/profilePhotoService";

/** Kartu akun: foto profil (bisa diganti sendiri), nama, email, peran, tautan ganti sandi. */
export function AccountSummaryCard({ email, roleLabel, scopeLines = [] }: { email: string | undefined; roleLabel: string; scopeLines?: string[] }) {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });
  const change = useChangeMyPhoto();
  const picker = useRef<HTMLInputElement>(null);
  const [removing, setRemoving] = useState(false);
  const name = me?.full_name || email?.split("@")[0];

  const onPick = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      await change.mutateAsync(file);
      toast.success("Foto profil diperbarui.");
    } catch (err) {
      toast.error(errorMessage(err, "Foto tidak dapat disimpan. Coba lagi."));
    }
  };

  const remove = async () => {
    try {
      await change.mutateAsync(null);
      toast.success("Foto profil dihapus.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
    setRemoving(false);
  };

  return (
    <section aria-label="Akun" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
      <div className="mb-4 flex flex-col items-center gap-3">
        <UserAvatar name={name} fileId={me?.photo_file_id} size="xl" />
        <div className="flex flex-wrap justify-center gap-2">
          <ActionButton size="sm" variant="outline" onClick={() => picker.current?.click()} disabled={change.isPending}>
            {change.isPending ? "Menyimpan…" : me?.photo_file_id ? "Ganti foto" : "Tambah foto"}
          </ActionButton>
          {me?.photo_file_id && (
            <ActionButton size="sm" variant="outline" onClick={() => setRemoving(true)} disabled={change.isPending}>
              Hapus foto
            </ActionButton>
          )}
        </div>
        <ControlInput
          ref={picker}
          type="file"
          accept="image/jpeg,image/png"
          capture="user"
          className="sr-only"
          aria-label="Pilih foto profil"
          onChange={(e) => void onPick(e)}
        />
      </div>
      <TextBlock className="font-medium">{name}</TextBlock>
      <TextBlock className="text-sm text-mist">{email}</TextBlock>
      <TextBlock className={scopeLines.length ? "text-sm text-mist" : "mb-4 text-sm text-mist"}>{roleLabel}</TextBlock>
      {scopeLines.map((l, i) => (
        <TextBlock key={l} className={i === scopeLines.length - 1 ? "mb-4 text-sm text-mist" : "text-sm text-mist"}>{l}</TextBlock>
      ))}
      <ActionButton asChild variant="outline">
        <InlineLink to="/change-password">Ganti sandi</InlineLink>
      </ActionButton>
      <ConfirmDialog
        open={removing}
        title="Hapus foto profil?"
        message="Foto diganti dengan inisial nama Anda."
        confirmLabel="Hapus foto"
        busy={change.isPending}
        onConfirm={() => void remove()}
        onClose={() => setRemoving(false)}
      />
    </section>
  );
}
