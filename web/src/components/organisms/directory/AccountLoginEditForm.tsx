import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField } from "@/components/molecules/Field";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { accountLoginSchema, type AccountLoginValues } from "@/schemas/accountSchemas";
import { useAccountAction } from "@/services/employeeService";

/**
 * HR/admin mengganti email login akun. Email harus unik; perangkat yang sedang masuk dikeluarkan
 * supaya kredensial lama tidak dipakai lagi.
 */
export function AccountLoginEditForm({ employeeId, login }: { employeeId: string; login: string }) {
  const action = useAccountAction(employeeId);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<AccountLoginValues>({ resolver: zodResolver(accountLoginSchema), defaultValues: { login } });

  // Setelah simpan, akun dimuat ulang dari server: isian ikut email terbaru.
  useEffect(() => {
    reset({ login });
  }, [login, reset]);

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await action.mutateAsync({ kind: "login", login: v.login.trim().toLowerCase() });
      toast.success("Email login diperbarui. Perangkat yang masuk dikeluarkan.");
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, ["login"]) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });

  return (
    <FormBlock onSubmit={onSubmit} noValidate className="flex flex-col gap-3" aria-label="Ganti email login">
      <TextBlock className="font-medium">Ganti email login</TextBlock>
      <TextBlock className="text-xs text-mist">
        Karyawan masuk memakai email ini. Setelah diganti, perangkat yang sedang masuk harus masuk ulang dengan email baru.
      </TextBlock>
      <FormErrorText message={formError} className="mb-0" />
      <TextField
        label="Email login"
        type="email"
        autoComplete="off"
        error={errors.login?.message}
        {...register("login")}
      />
      <ActionButton className="self-start" type="submit" variant="outline" disabled={isSubmitting || !isDirty || action.isPending}>
        Simpan email login
      </ActionButton>
    </FormBlock>
  );
}
