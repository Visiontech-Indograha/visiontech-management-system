import { AlertCircle, Timer } from "lucide-react";
import type { UseFormReturn } from "react-hook-form";
import logo from "@/assets/brand/logo-visiontech.png";
import { Alert, AlertDescription } from "@/components/atoms/Alert";
import { Button } from "@/components/atoms/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/atoms/Card";
import { Input } from "@/components/atoms/Input";
import { Label } from "@/components/atoms/Label";
import type { LoginValues } from "../loginSchema";

function mmss(total: number): string {
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * Kartu login: judul, galat/kunci sementara, email + password, tombol masuk.
 * State form & pengiriman dipegang Page; `lockSeconds` > 0 = login dikunci server (R-21).
 */
export function LoginForm({ admin, form, onSubmit, formError, lockSeconds }: {
  admin: boolean;
  form: UseFormReturn<LoginValues>;
  onSubmit: () => void;
  formError: string | null;
  lockSeconds: number;
}) {
  const { register, formState: { errors, isSubmitting } } = form;
  return (
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
              {lockSeconds > 0 ? (
                <Alert variant="destructive" data-testid="login-locked">
                  <Timer aria-hidden />
                  <AlertDescription>
                    Login dikunci sementara karena terlalu banyak percobaan gagal. Coba lagi dalam{" "}
                    <strong>{mmss(lockSeconds)}</strong>.
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
              <Button type="submit" className="h-11 w-full" disabled={isSubmitting || lockSeconds > 0}>
                {isSubmitting ? "Memproses..." : lockSeconds > 0 ? `Tunggu ${mmss(lockSeconds)}` : "Masuk"}
              </Button>
            </form>
          </CardContent>
        </Card>
  );
}
