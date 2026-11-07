import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { ApiError } from "@/lib/apiClient";
import { useSaveClient, type Client, type ClientInput } from "@/services/clientService";
import { namaKlienError } from "@/lib/inputRules";
import { ActionButton } from "@/components/molecules/ActionButton";

export function ClientFormDialog({
  client,
  onClose,
  onUseExisting,
}: {
  client: Client | null;
  onClose: () => void;
  /** Nama klien sudah ada (409 CLIENT_EXISTS): buka klien yang sudah ada alih-alih membuat duplikat. */
  onUseExisting?: (clientId: string) => void;
}) {
  const save = useSaveClient(client?.client_id);
  const [formError, setFormError] = useState<string | null>(null);
  const [existingId, setExistingId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ClientInput>({
    defaultValues: {
      client_code: client?.client_code ?? "",
      name: client?.name ?? "",
      pic_name: client?.pic_name ?? "",
      pic_phone: client?.pic_phone ?? "",
      address: client?.address ?? "",
    },
  });

  const onSubmit = async (values: ClientInput) => {
    setFormError(null);
    setExistingId(null);
    try {
      await save.mutateAsync({
        client_code: values.client_code.trim().toUpperCase(),
        name: values.name.trim(),
        pic_name: values.pic_name?.trim() || null,
        pic_phone: values.pic_phone?.trim() || null,
        address: values.address?.trim() || null,
      });
      toast.success(client ? "Data klien diperbarui." : "Klien baru berhasil ditambahkan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.code === "CLIENT_EXISTS" && typeof err.details.client_id === "string") {
        setExistingId(err.details.client_id);
      }
      setFormError(applyFieldErrors(err, setError) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  };

  return (
    <VmsDialog dirty={isDirty}
      open
      title={client ? "Ubah data klien" : "Tambah klien baru"}
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="client-form"
          submitLabel={client ? "Simpan Perubahan" : "Tambah Klien"}
        />
      }
    >
      <TextBlock className="mb-4 text-sm text-mist">
        {client
          ? "Perbarui informasi kontak dan alamat perusahaan klien."
          : "Daftarkan perusahaan klien untuk mengelola proyek dan penugasan pekerjaan."}
      </TextBlock>
      <FormBlock id="client-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}
        {existingId && onUseExisting && (
          <ActionButton type="button" variant="link" size="xs" className="text-primary font-medium p-0 h-auto"
            onClick={() => onUseExisting(existingId)}>
            Pakai klien yang sudah ada
          </ActionButton>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Kode Klien"
            placeholder="cth. PLN, IOH, TELKOM"
            error={errors.client_code?.message}
            {...register("client_code", {
              required: "Kode klien wajib diisi.",
              minLength: { value: 2, message: "Kode klien minimal 2 karakter." },
              maxLength: { value: 20, message: "Maksimal 20 karakter." },
              pattern: { value: /^[A-Za-z0-9_-]+$/, message: "Kode hanya huruf, angka, - dan _ (tanpa spasi)." },
            })}
          />
          <TextField
            label="Nama Perusahaan Klien"
            maxLength={150}
            placeholder="cth. PT Telekomunikasi Seluler"
            error={errors.name?.message}
            {...register("name", {
              validate: (v) => (v.trim() === "" ? "Nama klien wajib diisi." : (namaKlienError(v) ?? true)),
            })}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Nama PIC Klien (Opsional)"
            placeholder="cth. Bpk. Hendra Gunawan"
            error={errors.pic_name?.message}
            maxLength={100}
            {...register("pic_name")}
          />
          <TextField
            label="Nomor Telepon / WhatsApp PIC"
            placeholder="cth. 081234567890"
            error={errors.pic_phone?.message}
            maxLength={30}
            {...register("pic_phone", {
              pattern: { value: /^[0-9+()\-\s]{5,30}$/, message: "Nomor telepon hanya angka, +, -, ( ) dan spasi (min. 5)." },
            })}
          />
        </div>

        <TextAreaField
          label="Alamat Kantor Klien (Opsional)"
          placeholder="Alamat gedung atau operasional klien..."
          rows={3}
          maxLength={2000}
          error={errors.address?.message}
          {...register("address")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
