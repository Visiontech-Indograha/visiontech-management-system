import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Navigate, useNavigate } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import { ApiError } from "@/lib/apiClient";
import { changePassword } from "@/services/authService";
import { changePasswordSchema, type ChangePasswordValues } from "@/schemas/changePasswordSchema";
import { ChangePasswordTemplate } from "@/components/templates/auth/ChangePasswordTemplate";

/** Ganti sandi (wajib saat login pertama). Berhasil → token baru dipasang, kembali ke Beranda. */
export function ChangePasswordPage() {
  const { me, applyToken, logout } = useSession();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ChangePasswordValues>({ resolver: zodResolver(changePasswordSchema) });
  const { handleSubmit, setError } = form;

  if (!me) return <Navigate to="/login" replace />;

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setFormError(null);
    try {
      await applyToken(await changePassword(current_password, new_password));
      toast.success("Sandi diubah.");
      navigate("/", { replace: true });
    } catch (e) {
      if (e instanceof ApiError) {
        const fields = (e.details.fields ?? {}) as Record<string, string>;
        if (fields.current_password) setError("current_password", { message: fields.current_password });
        else if (fields.password) setError("new_password", { message: fields.password });
        else setFormError(e.message);
      } else {
        setFormError("Sandi tidak dapat diubah. Coba lagi.");
      }
    }
  });

  return (
    <ChangePasswordTemplate
      form={form} onSubmit={onSubmit} formError={formError}
      forced={!!me.must_change_password}
      onLogout={() => void logout()}
    />
  );
}
