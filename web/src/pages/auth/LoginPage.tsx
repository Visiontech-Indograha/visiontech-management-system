import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "@/stores/sessionStore";
import { ApiError } from "@/lib/apiClient";
import { LoginTemplate } from "@/components/templates/auth/LoginTemplate";
import { loginSchema, type LoginValues } from "@/schemas/loginSchema";
import { safeRedirectPath } from "@/lib/safeRedirect";
import { useSetupStatus } from "@/services/setupService";
import { useLockCountdown } from "@/hooks/useLockCountdown";

/** Kedua halaman login memakai endpoint auth yang sama. */
export function LoginPage({ admin = false }: { admin?: boolean }) {
  const { me, login } = useSession();
  const [formError, setFormError] = useState<string | null>(null);
  const [formErrorCode, setFormErrorCode] = useState<string | null>(null);
  const setupStatus = useSetupStatus();
  const lockLeft = useLockCountdown();
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const { handleSubmit } = form;

  const tujuan = safeRedirectPath((useLocation().state as { from?: unknown } | null)?.from);
  if (me) return <Navigate to={tujuan} replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    setFormErrorCode(null);
    try {
      await login(email, password, admin);
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Tidak dapat masuk. Coba lagi.");
      setFormErrorCode(e instanceof ApiError ? e.code : null);
      const retry = e instanceof ApiError && e.code === "LOCKED" ? Number(e.details.retry_after_seconds) : 0;
      if (retry > 0) lockLeft.start(retry);
    }
  });

  return (
    <LoginTemplate
      admin={admin}
      form={form}
      onSubmit={onSubmit}
      formError={formError}
      formErrorCode={formErrorCode}
      lockSeconds={lockLeft.seconds}
      showSetupLink={!!setupStatus.data?.needs_setup}
    />
  );;
}
