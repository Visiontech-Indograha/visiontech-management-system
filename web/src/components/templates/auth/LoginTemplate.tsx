import type { UseFormReturn } from "react-hook-form";
import { AndroidAppLink } from "@/components/organisms/auth/AndroidAppLink";
import { LoginBrandPanel } from "@/components/organisms/auth/LoginBrandPanel";
import { LoginForm } from "@/components/organisms/auth/LoginForm";
import type { LoginValues } from "@/schemas/loginSchema";

/** Kerangka login: panel merek (desktop) + kartu login + tautan unduh aplikasi Android. */
export function LoginTemplate({ admin, form, onSubmit, formError, lockSeconds }: {
  admin: boolean;
  form: UseFormReturn<LoginValues>;
  onSubmit: () => void;
  formError: string | null;
  lockSeconds: number;
}) {
  return (
    <main className="no-reveal grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Panel brand (desktop) — navy Visiontech + aksen emas */}
      <LoginBrandPanel />

      <section className="flex flex-col items-center justify-center gap-4 px-4 py-10">
        <LoginForm admin={admin} form={form} onSubmit={onSubmit} formError={formError} lockSeconds={lockSeconds} />
        <AndroidAppLink />
      </section>
    </main>
  );
}
