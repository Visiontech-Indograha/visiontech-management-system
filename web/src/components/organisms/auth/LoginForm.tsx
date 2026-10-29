import type { UseFormReturn } from "react-hook-form";
import logo from "@/assets/brand/logo-visiontech.png";
import type { LoginValues } from "@/schemas/loginSchema";
import { Notice, NoticeDescription } from "@/components/molecules/Notice";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Panel, PanelContent, PanelDescription, PanelHeader, PanelTitle } from "@/components/molecules/Panel";
import { StyledInput, StyledLabel } from "@/components/molecules/InputControls";
import { AlertCircle, Timer } from "@/components/molecules/Glyphs";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { FormBlock } from "@/components/molecules/FormBlock";

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
        <Panel className="w-full max-w-sm gap-5">
          <PanelHeader>
            <ImageView src={logo} alt="Visiontech Indograha" className="mb-3 h-10 w-auto self-start lg:hidden" />
            <PanelTitle>
              <TextBlock as="h1" className="text-title-lg text-ink">{admin ? "Masuk sebagai Admin" : "Selamat datang"}</TextBlock>
            </PanelTitle>
            <PanelDescription>Masuk dengan email dan password akun kantor Anda.</PanelDescription>
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
                <Notice variant="destructive">
                  <AlertCircle aria-hidden />
                  <NoticeDescription>{formError}</NoticeDescription>
                </Notice>
              )}
              <div className="space-y-1.5">
                <StyledLabel htmlFor="email">Email</StyledLabel>
                <StyledInput id="email" autoComplete="email" autoCapitalize="none" placeholder="nama@visiontech.id" {...register("email")} />
                {errors.email && <TextBlock className="text-sm text-destructive">{errors.email.message}</TextBlock>}
              </div>
              <div className="space-y-1.5">
                <StyledLabel htmlFor="password">Password</StyledLabel>
                <StyledInput id="password" type="password" autoComplete="current-password" {...register("password")} />
                {errors.password && <TextBlock className="text-sm text-destructive">{errors.password.message}</TextBlock>}
              </div>
              <ActionButton type="submit" className="h-11 w-full" disabled={isSubmitting || lockSeconds > 0}>
                {isSubmitting ? "Memproses..." : lockSeconds > 0 ? `Tunggu ${mmss(lockSeconds)}` : "Masuk"}
              </ActionButton>
            </FormBlock>
          </PanelContent>
          <TextBlock className="text-center text-xs text-muted-foreground">Versi {__APP_VERSION__}</TextBlock>
        </Panel>
  );
}
