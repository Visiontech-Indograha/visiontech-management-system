import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useSession } from "@/app/session";
import { Button } from "@/components/atoms/Button";
import { TextField } from "@/components/molecules/Field";
import { api, ApiError } from "@/lib/apiClient";
import type { TokenOut } from "@/lib/types";

const schema = z
  .object({
    current_password: z.string().min(1, "Password saat ini wajib diisi."),
    new_password: z
      .string()
      .min(8, "Password minimal 8 karakter.")
      .regex(/[A-Za-z]/, "Password harus memuat huruf.")
      .regex(/\d/, "Password harus memuat angka."),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    path: ["confirm"],
    message: "Konfirmasi password tidak sama.",
  });
type Values = z.infer<typeof schema>;

export function ChangePasswordPage() {
  const { me, applyToken } = useSession();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  if (!me) return <Navigate to="/login" replace />;

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setFormError(null);
    try {
      const { data } = await api.post<TokenOut>("/auth/change-password", { current_password, new_password });
      await applyToken(data);
      toast.success("Password diubah.");
      navigate("/", { replace: true });
    } catch (e) {
      if (e instanceof ApiError) {
        const fields = (e.details.fields ?? {}) as Record<string, string>;
        if (fields.current_password) setError("current_password", { message: fields.current_password });
        else if (fields.password) setError("new_password", { message: fields.password });
        else setFormError(e.message);
      } else {
        setFormError("Password tidak dapat diubah. Coba lagi.");
      }
    }
  });

  return (
    <main className="mx-auto mt-16 w-full max-w-sm px-4">
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
    </main>
  );
}
