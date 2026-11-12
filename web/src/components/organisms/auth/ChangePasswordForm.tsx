import type { UseFormReturn } from "react-hook-form";
import { PasswordField } from "@/components/molecules/Field";
import type { ChangePasswordValues } from "@/schemas/changePasswordSchema";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";

/**
 * Form ganti password: judul, galat umum, tiga field, tombol simpan.
 * State form & pengiriman dipegang Page (`form`, `onSubmit`); komponen ini hanya menampilkan.
 */
export function ChangePasswordForm({ form, onSubmit, formError, forced = false, onLogout }: {
  form: UseFormReturn<ChangePasswordValues>;
  onSubmit: () => void;
  formError: string | null;
  /** Sandi sementara: halaman lain tertutup, jadi tampilkan penjelasan dan tombol Keluar. */
  forced?: boolean;
  onLogout?: () => void;
}) {
  const { register, formState: { errors, isSubmitting } } = form;
  return (
    <>
      <TextBlock as="h1" className="mb-1 text-2xl font-semibold">Ganti sandi</TextBlock>
      <TextBlock className="mb-6 text-mist">{forced
          ? "Sandi Anda masih sandi sementara. Ganti dengan sandi baru sebelum memakai aplikasi."
          : "Masukkan sandi saat ini dan sandi baru."}</TextBlock>
      <FormBlock onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <PasswordField
          label="Sandi saat ini"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <PasswordField
          label="Sandi baru"
          autoComplete="new-password"
          hint="Minimal 8 karakter, memuat huruf dan angka."
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <PasswordField
          label="Ulangi sandi baru"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />
        <ActionButton type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Menyimpan..." : "Ganti sandi"}
        </ActionButton>
      </FormBlock>
      {forced && onLogout && (
        <ActionButton type="button" variant="ghost" className="mt-3 w-full" onClick={onLogout}>
          Keluar
        </ActionButton>
      )}
    </>
  );
}
