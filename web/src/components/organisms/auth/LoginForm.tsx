import { useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import logo from "@/assets/brand/logo-visiontech.png";
import type { LoginValues } from "@/schemas/loginSchema";
import { Notice, NoticeDescription } from "@/components/molecules/Notice";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DeviceLimitHelpDialog } from "@/components/organisms/auth/DeviceLimitHelpDialog";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { StyledInput, StyledLabel } from "@/components/molecules/InputControls";
import { AlertCircle, Eye, EyeOff, Timer } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { InlineLink } from "@/components/molecules/Links";
import { FormBlock } from "@/components/molecules/FormBlock";

function mmss(total: number): string {
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * Kartu login: judul, galat/kunci sementara, email + password, tombol masuk.
 * State form & pengiriman dipegang Page; `lockSeconds` > 0 = login dikunci server (R-21).
 */
export function LoginForm({ admin, form, onSubmit, formError, formErrorCode = null, lockSeconds, showSetupLink = false }: {
  admin: boolean;
  form: UseFormReturn<LoginValues>;
  onSubmit: () => void;
  formError: string | null;
  /** Kode galat API (mis. NOT_OFFICE_ACCOUNT, MAX_DEVICES_REACHED) untuk petunjuk tambahan di bawah pesan. */
  formErrorCode?: string | null;
  lockSeconds: number;
  /** Tautan ke penyiapan awal; hanya bila server belum punya Super Admin. */
  showSetupLink?: boolean;
}) {
  const { register, formState: { errors, isSubmitting } } = form;
  const [helpOpen, setHelpOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  return (
    <>
        <Panel className="w-full max-w-sm gap-5">
          <PanelHeader>
            <ImageView src={logo} alt="Visiontech Indograha" className="mb-3 h-10 w-auto self-start lg:hidden" />
            <PanelTitle>
              <TextBlock as="h1" className="text-title-lg text-ink">{admin ? "Masuk sebagai Admin" : "Selamat datang"}</TextBlock>
            </PanelTitle>
            <PanelDescription>Masuk dengan email dan sandi akun kantor Anda.</PanelDescription>
          </PanelHeader>
          <PanelContent>
            <FormBlock onSubmit={onSubmit} noValidate className="space-y-4">
              {lockSeconds > 0 ? (
                <Notice variant="destructive" data-testid="login-locked">
                  <Timer aria-hidden />
                  <NoticeDescription>
                    Login dikunci sementara karena terlalu banyak percobaan gagal. Coba lagi dalam{" "}
                    <TextBlock as="strong">{mmss(lockSeconds)}</TextBlock>.
                  </NoticeDescription>
                </Notice>
              ) : formError && (
                <Notice variant="destructive" data-testid="login-error">
                  <AlertCircle aria-hidden />
                  <NoticeDescription>
                    {formError}
                    {formErrorCode === "NOT_OFFICE_ACCOUNT" && (
                      <TextBlock as="span" className="mt-1 block text-xs">
                        Akun karyawan lapangan masuk lewat aplikasi Visiontech di HP. Unduh aplikasinya di bawah form ini.
                      </TextBlock>
                    )}
                    {formErrorCode === "MAX_DEVICES_REACHED" && (
                      <ActionButton
                        type="button"
                        variant="link"
                        className="mt-1 h-auto p-0 text-xs"
                        onClick={() => setHelpOpen(true)}
                      >
                        Lihat cara mengeluarkan perangkat lama
                      </ActionButton>
                    )}
                  </NoticeDescription>
                </Notice>
              )}
              <div className="space-y-1.5">
                <StyledLabel htmlFor="email">Email</StyledLabel>
                <StyledInput id="email" autoComplete="email" autoCapitalize="none" placeholder="nama@visiontech.id" {...register("email")} />
                {errors.email && <TextBlock className="text-sm text-destructive">{errors.email.message}</TextBlock>}
              </div>
              <div className="space-y-1.5">
                <StyledLabel htmlFor="password">Sandi</StyledLabel>
                <div className="relative">
                  <StyledInput
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    className="pr-12"
                    {...register("password")}
                  />
                  <ActionButton
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                    className="absolute right-0 top-0 h-full min-h-[44px] min-w-[44px] rounded-r-md px-3 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </ActionButton>
                </div>
                {errors.password && <TextBlock className="text-sm text-destructive">{errors.password.message}</TextBlock>}
              </div>
              <ActionButton type="submit" className="h-11 w-full" disabled={isSubmitting || lockSeconds > 0}>
                {isSubmitting ? "Memproses..." : lockSeconds > 0 ? `Tunggu ${mmss(lockSeconds)}` : "Masuk"}
              </ActionButton>
            </FormBlock>
            {showSetupLink && (
              <TextBlock className="mt-4 text-center text-sm">
                Instalasi baru?{" "}
                <InlineLink to="/setup" className="font-medium text-brand-700 underline">Siapkan akun admin pertama</InlineLink>
              </TextBlock>
            )}
          </PanelContent>
          <TextBlock className="text-center text-xs text-muted-foreground">Versi {__APP_VERSION__}</TextBlock>
        </Panel>
        <DeviceLimitHelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}
