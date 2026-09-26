import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { AlertCircle } from "lucide-react";
import { useSession } from "@/app/session";
import logo from "@/assets/brand/logo-visiontech.png";
import logoWhite from "@/assets/brand/logo-visiontech-white.png";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";

const schema = z.object({
  email: z.string().trim().email("Format email tidak valid.").min(1, "Email wajib diisi."),
  password: z.string().min(1, "Password wajib diisi."),
});
type Values = z.infer<typeof schema>;

/** Kedua halaman login memakai endpoint auth yang sama. */
export function LoginPage({ admin = false }: { admin?: boolean }) {
  const { me, login } = useSession();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  if (me) return <Navigate to="/" replace />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      await login(email, password, admin);
      navigate("/", { replace: true });
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Tidak dapat masuk. Coba lagi.");
    }
  });

  return (
    <main className="grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Panel brand (desktop) — navy Visiontech + aksen emas */}
      <section aria-hidden className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 size-96 rounded-full bg-brand-600/60" />
        <div className="absolute -bottom-32 -left-16 size-80 rounded-full bg-brand-800/70" />
        <div className="relative inline-flex w-fit rounded-panel bg-white px-5 py-3 shadow-card">
          <img src={logoWhite} alt="" className="h-10 w-auto" />
        </div>
        <div className="relative max-w-md">
          <span className="mb-4 block h-1 w-12 rounded-full bg-gold" />
          <p className="text-display text-white">Pekerjaan lapangan, rapi dalam satu tempat.</p>
          <p className="mt-3 text-body text-brand-100">SK penugasan, absensi, laporan harian, aset, dan dokumen bertanda tangan digital.</p>
        </div>
        <p className="relative text-caption text-brand-200">© PT Visiontech Indograha</p>
      </section>

      <section className="flex items-center justify-center px-4 py-10">
        <Card className="w-full max-w-sm gap-5">
          <CardHeader>
            <img src={logo} alt="Visiontech Indograha" className="mb-3 h-10 w-auto self-start lg:hidden" />
            <CardTitle>
              <h1 className="text-title-lg text-ink">{admin ? "Masuk sebagai Admin" : "Selamat datang"}</h1>
            </CardTitle>
            <CardDescription>Masuk dengan email dan password akun kantor Anda.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} noValidate className="space-y-4">
              {formError && (
                <Alert variant="destructive">
                  <AlertCircle aria-hidden />
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" autoComplete="email" autoCapitalize="none" placeholder="nama@visiontech.co.id" {...register("email")} />
                {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
                {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
              </div>
              <Button type="submit" className="h-11 w-full" disabled={isSubmitting}>
                {isSubmitting ? "Memproses..." : "Masuk"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
