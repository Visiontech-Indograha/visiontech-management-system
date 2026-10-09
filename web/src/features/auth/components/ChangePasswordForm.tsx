import type { UseFormReturn } from "react-hook-form";
import { Button } from "@/components/atoms/Button";
import { TextField } from "@/components/molecules/Field";
import type { ChangePasswordValues } from "../changePasswordSchema";

/**
 * Form ganti password: judul, galat umum, tiga field, tombol simpan.
 * State form & pengiriman dipegang Page (`form`, `onSubmit`); komponen ini hanya menampilkan.
 */
export function ChangePasswordForm({ form, onSubmit, formError }: {
  form: UseFormReturn<ChangePasswordValues>;
  onSubmit: () => void;
  formError: string | null;
}) {
  const { register, formState: { errors, isSubmitting } } = form;
  return (
    <>
      <h1 className="mb-1 text-2xl font-semibold">Ganti password</h1>
      <p className="mb-6 text-mist">Masukkan password saat ini dan password baru.</p>
      <form onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField
          label="Password saat ini"
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <TextField
          label="Password baru"
          type="password"
          autoComplete="new-password"
          hint="Minimal 8 karakter, memuat huruf dan angka."
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <TextField
          label="Ulangi password baru"
          type="password"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Menyimpan..." : "Ganti password"}
        </Button>
      </form>
    </>
  );
}
