import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { SetupTemplate } from "@/components/templates/auth/SetupTemplate";
import { ApiError } from "@/lib/apiClient";
import { applyFieldErrors } from "@/lib/errors";
import { setupSchema, type SetupValues } from "@/schemas/setupSchema";
import { createFirstAdmin, useSetupStatus } from "@/services/setupService";

const KNOWN_FIELDS = ["setup_token", "full_name", "email", "password"] as const;

const PESAN_KODE: Record<string, string> = {
  SETUP_TOKEN_INVALID: "Kode penyiapan salah. Periksa kode dari operator lalu coba lagi.",
  SETUP_LOCKED: "Instalasi ini sudah disiapkan. Silakan masuk.",
  EMAIL_TAKEN: "Email ini sudah dipakai akun lain. Pakai email yang berbeda.",
};

/** Penyiapan awal (publik): buat Super Admin pertama, lalu ke halaman masuk. */
export function SetupPage() {
  const status = useSetupStatus();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<SetupValues>({ resolver: zodResolver(setupSchema) });

  const onSubmit = form.handleSubmit(async ({ setup_token, full_name, email, password }) => {
    setFormError(null);
    try {
      await createFirstAdmin({ setup_token, full_name, email, password });
      toast.success("Akun Super Admin dibuat. Silakan masuk.");
      navigate("/login", { replace: true });
    } catch (e) {
      if (applyFieldErrors(e, form.setError, KNOWN_FIELDS)) return;
      if (e instanceof ApiError && PESAN_KODE[e.code]) {
        setFormError(PESAN_KODE[e.code]);
        if (e.code === "SETUP_LOCKED") void status.refetch();
      } else {
        setFormError("Penyiapan belum berhasil. Coba lagi sebentar lagi.");
      }
    }
  });

  return (
    <SetupTemplate
      status={status.data}
      isPending={status.isPending}
      isError={status.isError}
      onRetry={() => void status.refetch()}
      form={form}
      onSubmit={onSubmit}
      formError={formError}
    />
  );
}
