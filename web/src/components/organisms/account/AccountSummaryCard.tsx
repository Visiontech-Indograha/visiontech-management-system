import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/services/authService";
import { useFileUrl } from "@/hooks/useFileUrl";

/** Kartu akun: foto profil, email, peran, tautan ganti password. */
export function AccountSummaryCard({ email, roleLabel }: { email: string | undefined; roleLabel: string }) {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });

  // Presigned URL: <img src> tidak bisa mengirim header Authorization.
  const { data: photoUrl } = useFileUrl(me?.photo_file_id, "view");

  return (
        <section aria-label="Akun" className="rounded-panel border border-line bg-surface px-5 py-4 shadow-card">
          {photoUrl && (
            <div className="mb-4 flex justify-center">
              <ImageView
                src={photoUrl}
                alt={email ?? "Foto profil"}
                className="h-24 w-24 rounded-full object-cover"
              />
            </div>
          )}
          <TextBlock className="font-medium">{email}</TextBlock>
          <TextBlock className="mb-4 text-sm text-mist">{roleLabel}</TextBlock>
          <ActionButton asChild variant="outline">
            <InlineLink to="/change-password">Ganti password</InlineLink>
          </ActionButton>
        </section>
  );
}
