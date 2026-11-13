import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { deviceBody, deviceDefaults } from "@/lib/hikvisionForm";
import { deviceSchema, type DeviceValues } from "@/schemas/hikvisionSchemas";
import { useOffices } from "@/services/employeeService";
import { useCreateDevice, useUpdateDevice, type Perangkat, type TokenBaru } from "@/services/hikvisionService";

const KNOWN = ["office_id", "name", "ip_address", "http_port", "serial_no", "model", "catatan"] as const;

const failureText = (err: unknown, setError: Parameters<typeof applyFieldErrors>[1]) =>
  applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err);

const dialogTitle = (d?: Perangkat) => (d ? "Ubah mesin absensi" : "Tambah mesin absensi");

/** Tambah/ubah mesin absensi. Mesin baru mulai di mode Bayangan; tautan penerima diteruskan lewat `onCreated`. */
export function DeviceFormDialog({ device, onClose, onCreated }: {
  device?: Perangkat;
  onClose: () => void;
  onCreated?: (d: Perangkat, link: TokenBaru) => void;
}) {
  const offices = useOffices();
  const create = useCreateDevice();
  const update = useUpdateDevice(device?.device_id ?? "");
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting, isDirty } } = useForm<DeviceValues>({
    resolver: zodResolver(deviceSchema),
    defaultValues: deviceDefaults(device),
  });

  const createDevice = async (office_id: string, body: ReturnType<typeof deviceBody>) => {
    const r = await create.mutateAsync({ ...body, office_id });
    toast.success("Mesin absensi ditambahkan.");
    return [r.perangkat, r.penerima] as const;
  };

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const body = deviceBody(v);
    try {
      if (!device) return void onCreated?.(...(await createDevice(v.office_id, body)));
      await update.mutateAsync(body);
      toast.success("Mesin absensi diubah.");
      onClose();
    } catch (err) {
      setFormError(failureText(err, setError));
    }
  });

  return (
    <VmsDialog
      dirty={isDirty}
      open
      title={dialogTitle(device)}
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={isSubmitting} formId="hik-device-form" />}
    >
      <FormBlock id="hik-device-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <SelectField label="Kantor" disabled={!!device} error={errors.office_id?.message} {...register("office_id")}>
          <ControlOption value="">Pilih kantor</ControlOption>
          {offices.data?.map((o) => (
            <ControlOption key={o.id} value={o.id}>{o.name}</ControlOption>
          ))}
        </SelectField>
        <TextField label="Nama mesin" maxLength={100} error={errors.name?.message} {...register("name")} />
        <div className="grid gap-x-3 md:grid-cols-2">
          <TextField label="Alamat IP mesin" maxLength={45} hint="Contoh: 192.168.1.20" error={errors.ip_address?.message} {...register("ip_address")} />
          <TextField label="Port" inputMode="numeric" error={errors.http_port?.message} {...register("http_port")} />
        </div>
        <TextField label="Nomor seri" maxLength={64} error={errors.serial_no?.message} {...register("serial_no")} />
        <TextField label="Model (boleh kosong)" maxLength={64} error={errors.model?.message} {...register("model")} />
        <TextField label="Catatan (boleh kosong)" maxLength={500} error={errors.catatan?.message} {...register("catatan")} />
        <SelectField label="Pemakaian" error={errors.aktif?.message} {...register("aktif")}>
          <ControlOption value="ya">Mesin dipakai</ControlOption>
          <ControlOption value="tidak">Mesin dimatikan</ControlOption>
        </SelectField>
      </FormBlock>
    </VmsDialog>
  );
}
