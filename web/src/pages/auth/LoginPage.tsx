import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router-dom";
import { useSession } from "@/app/session";
import { ApiError } from "@/lib/apiClient";
import { AndroidAppLink } from "@/components/organisms/auth/AndroidAppLink";
import { LoginBrandPanel } from "@/components/organisms/auth/LoginBrandPanel";
import { LoginForm } from "@/components/organisms/auth/LoginForm";
import { loginSchema, type LoginValues } from "@/schemas/loginSchema";
import { useLockCountdown } from "@/hooks/useLockCountdown";

/** Kedua halaman login memakai endpoint auth yang sama. */
export function LoginPage({ admin = false }: { admin?: boolean }) {
  const { me, login } = useSession();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const lockLeft = useLockCountdown();
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const { handleSubmit } = form;

  if (me) return <Navigate to="/" replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      await login(email, password, admin);
      navigate("/", { replace: true });
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Tidak dapat masuk. Coba lagi.");
      const retry = e instanceof ApiError && e.code === "LOCKED" ? Number(e.details.retry_after_seconds) : 0;
      if (retry > 0) lockLeft.start(retry);
    }
  });

  return (
    <main className="no-reveal grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Panel brand (desktop) — navy Visiontech + aksen emas */}
      <LoginBrandPanel />

      <section className="flex flex-col items-center justify-center gap-4 px-4 py-10">
        <LoginForm admin={admin} form={form} onSubmit={onSubmit} formError={formError} lockSeconds={lockLeft.seconds} />
        <AndroidAppLink />
      </section>
    </main>
  );
}
