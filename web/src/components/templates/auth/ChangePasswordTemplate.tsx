import type { UseFormReturn } from "react-hook-form";
import { ChangePasswordForm } from "@/components/organisms/auth/ChangePasswordForm";
import type { ChangePasswordValues } from "@/schemas/changePasswordSchema";

/** Kerangka ganti password: kartu sempit di tengah. */
export function ChangePasswordTemplate(props: {
  form: UseFormReturn<ChangePasswordValues>;
  onSubmit: () => void;
  formError: string | null;
  forced?: boolean;
  onLogout?: () => void;
}) {
  return (
    <main className="mx-auto mt-16 w-full max-w-sm px-4">
      <ChangePasswordForm {...props} />
    </main>
  );
}
