import type { UseFormReturn } from "react-hook-form";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { InlineLink } from "@/components/molecules/Links";
import type { SetupStatus } from "@/services/setupService";
import type { SetupValues } from "@/schemas/setupSchema";

/**
 * Kartu penyiapan awal: lima kondisi (memuat, galat, sudah disiapkan, belum diaktifkan, form).
 * State form dan pengiriman dipegang Page.
 */
export function SetupForm({ status, isPending, isError, onRetry, form, onSubmit, formError }: {
  status: SetupStatus | undefined;
  isPending: boolean;
  isError: boolean;
  onRetry: () => void;
  form: UseFormReturn<SetupValues>;
  onSubmit: () => void;
  formError: string | null;
}) {
  const { register, formState: { errors, isSubmitting } } = form;
  return (
    <Panel className="w-full max-w-sm gap-5">
      <PanelHeader>
        <PanelTitle>
          <TextBlock as="h1" className="text-title-lg text-ink">Penyiapan awal</TextBlock>
        </PanelTitle>
        <PanelDescription>Buat akun Super Admin pertama untuk instalasi ini.</PanelDescription>
      </PanelHeader>
      <PanelContent>
        {isPending && (
          <div role="status" aria-live="polite" className="space-y-3">
            <TextBlock className="sr-only">Memeriksa status penyiapan</TextBlock>
            <LoadingBar className="h-10 w-full" />
            <LoadingBar className="h-10 w-full" />
          </div>
        )}
        {isError && (
          <div className="space-y-3">
            <FormErrorText message="Status penyiapan belum bisa dimuat. Periksa koneksi Anda." className="" />
            <ActionButton type="button" variant="outline" onClick={onRetry}>Coba lagi</ActionButton>
          </div>
        )}
        {status && !status.needs_setup && (
          <div className="space-y-3">
            <TextBlock>Instalasi ini sudah disiapkan. Silakan masuk.</TextBlock>
            <InlineLink to="/login" className="text-sm font-medium text-brand-700 underline">Ke halaman masuk</InlineLink>
          </div>
        )}
        {status && status.needs_setup && !status.enabled && (
          <TextBlock role="status">Hubungi operator untuk mengaktifkan penyiapan.</TextBlock>
        )}
        {status && status.needs_setup && status.enabled && (
          <FormBlock onSubmit={onSubmit} noValidate>
            <FormErrorText message={formError} />
            <TextField
              label="Kode penyiapan"
              autoComplete="off"
              hint="Kode ini diberikan operator server."
              error={errors.setup_token?.message}
              {...register("setup_token")}
            />
            <TextField label="Nama lengkap" autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
            <TextField
              label="Email"
              autoComplete="email"
              autoCapitalize="none"
              placeholder="nama@visiontech.id"
              error={errors.email?.message}
              {...register("email")}
            />
            <TextField
              label="Sandi"
              type="password"
              autoComplete="new-password"
              hint="12 sampai 128 karakter."
              error={errors.password?.message}
              {...register("password")}
            />
            <TextField
              label="Ulangi sandi"
              type="password"
              autoComplete="new-password"
              error={errors.confirm?.message}
              {...register("confirm")}
            />
            <ActionButton type="submit" className="h-11 w-full" disabled={isSubmitting}>
              {isSubmitting ? "Menyimpan..." : "Buat akun Super Admin"}
            </ActionButton>
          </FormBlock>
        )}
      </PanelContent>
    </Panel>
  );
}
