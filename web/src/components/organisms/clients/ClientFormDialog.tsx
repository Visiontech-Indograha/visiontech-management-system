import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useSaveClient, type Client, type ClientInput } from "@/services/clientService";

export function ClientFormDialog({
  client,
  onClose,
}: {
  client: Client | null;
  onClose: () => void;
}) {
  const save = useSaveClient(client?.client_id);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
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
    } catch {
      setFormError("Gagal menyimpan data klien. Pastikan kode klien belum pernah digunakan.");
    }
  };

  return (
    <VmsDialog
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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Kode Klien"
            placeholder="cth. PLN, IOH, TELKOM"
            error={errors.client_code?.message}
            {...register("client_code", {
              required: "Kode klien wajib diisi.",
              maxLength: { value: 20, message: "Maksimal 20 karakter." },
            })}
          />
          <TextField
            label="Nama Perusahaan Klien"
            placeholder="cth. PT Telekomunikasi Seluler"
            error={errors.name?.message}
            {...register("name", {
              required: "Nama klien wajib diisi.",
            })}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Nama PIC Klien (Opsional)"
            placeholder="cth. Bpk. Hendra Gunawan"
            error={errors.pic_name?.message}
            {...register("pic_name")}
          />
          <TextField
            label="Nomor Telepon / WhatsApp PIC"
            placeholder="cth. 081234567890"
            error={errors.pic_phone?.message}
            {...register("pic_phone")}
          />
        </div>

        <TextAreaField
          label="Alamat Kantor Klien (Opsional)"
          placeholder="Alamat gedung atau operasional klien..."
          rows={3}
          error={errors.address?.message}
          {...register("address")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
