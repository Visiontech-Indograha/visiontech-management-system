import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { AlertCircle, Smartphone, Timer } from "lucide-react";
import { useSession } from "@/app/session";
import logo from "@/assets/brand/logo-visiontech.png";
import { Alert, AlertDescription } from "@/components/atoms/Alert";
import { Button } from "@/components/atoms/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/atoms/Card";
import { Input } from "@/components/atoms/Input";
import { Label } from "@/components/atoms/Label";
import { ApiError, api } from "@/lib/api";

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
  const lockLeft = useLockCountdown();
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
      const retry = e instanceof ApiError && e.code === "LOCKED" ? Number(e.details.retry_after_seconds) : 0;
      if (retry > 0) lockLeft.start(retry);
    }
  });

  return (
    <main className="no-reveal grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Panel brand (desktop) — navy Visiontech + aksen emas */}
      <section aria-hidden className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 size-96 rounded-full bg-brand-600/60" />
        <div className="absolute -bottom-32 -left-16 size-80 rounded-full bg-brand-800/70" />
        <div className="relative inline-flex w-fit rounded-panel bg-white px-5 py-3 shadow-card">
          <img src={logo} alt="" className="h-10 w-auto" />
        </div>
        <div className="relative max-w-md">
          <span className="mb-4 block h-1 w-12 rounded-full bg-gold" />
          <p className="text-display text-white">Pekerjaan lapangan, rapi dalam satu tempat.</p>
          <p className="mt-3 text-body text-brand-100">Rencana Kerja penugasan, absensi, laporan harian, aset, dan dokumen bertanda tangan digital.</p>
        </div>
        <p className="relative text-caption text-brand-200">© PT Visiontech Indograha</p>
      </section>

      <section className="flex flex-col items-center justify-center gap-4 px-4 py-10">
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
              {lockLeft.seconds > 0 ? (
                <Alert variant="destructive" data-testid="login-locked">
                  <Timer aria-hidden />
                  <AlertDescription>
                    Login dikunci sementara karena terlalu banyak percobaan gagal. Coba lagi dalam{" "}
                    <strong>{mmss(lockLeft.seconds)}</strong>.
                  </AlertDescription>
                </Alert>
              ) : formError && (
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
              <Button type="submit" className="h-11 w-full" disabled={isSubmitting || lockLeft.seconds > 0}>
                {isSubmitting ? "Memproses..." : lockLeft.seconds > 0 ? `Tunggu ${mmss(lockLeft.seconds)}` : "Masuk"}
              </Button>
            </form>
          </CardContent>
        </Card>
        <AndroidAppLink />
      </section>
    </main>
  );
}

function mmss(total: number): string {
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/** Hitung mundur cooldown login (R-21) dari `retry_after_seconds` server; server tetap penentunya. */
function useLockCountdown() {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (until <= now) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [until, now]);
  return {
    seconds: Math.max(0, Math.ceil((until - now) / 1000)),
    start: (secs: number) => {
      const t = Date.now();
      setNow(t);
      setUntil(t + secs * 1000);
    },
  };
}

type AndroidRelease = {
  latest_build: number | null;
  latest_version: string | null;
  download: { size: number } | null;
};

/** Tautan pemasangan pertama aplikasi HP (docs/32) — hanya tampil bila sudah ada rilis di portal. */
function AndroidAppLink() {
  const { data } = useQuery({
    queryKey: ["app-android-latest"],
    queryFn: async () =>
      (await api.get<AndroidRelease>("/app/android/update", { params: { build: 0, abi: "arm64-v8a" } })).data,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
  if (!data?.latest_build || !data.download) return null;
  const mb = (data.download.size / (1024 * 1024)).toFixed(0);
  return (
    <a
      href={`${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1/app/android/latest.apk`}
      className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium text-primary hover:underline"
      data-testid="unduh-aplikasi-android"
    >
      <Smartphone aria-hidden className="size-4" />
      Unduh aplikasi Android · versi {data.latest_version} (build {data.latest_build}) · {mb} MB
    </a>
  );
}
