import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import {
  type MessPlace,
  useCreateMessPlace,
  useUpdateMessPlace,
} from "@/services/messService";

/** Angka opsional: kolom kosong → null (bukan 0 yang menunjuk ke tengah laut). */
const optionalNumber = (min: number, max: number, label: string) =>
  z
    .union([z.number(), z.nan(), z.null()])
    .transform((v) => (typeof v === "number" && !Number.isNaN(v) ? v : null))
    .refine(
      (v) => v === null || (v >= min && v <= max),
      `${label} harus di antara ${min} dan ${max}.`,
    );

const placeSchema = z.object({
  mess_name: z.string().trim().min(2, "Nama mess minimal 2 karakter.").max(150),
  city: z.string().trim().min(2, "Kota minimal 2 karakter.").max(100),
  address: z.string().trim().min(5, "Alamat lengkap wajib diisi.").max(500),
  latitude: optionalNumber(-90, 90, "Latitude"),
  longitude: optionalNumber(-180, 180, "Longitude"),
  capacity: z
    .union([z.number(), z.nan(), z.null()])
    .transform((v) => (typeof v === "number" && !Number.isNaN(v) ? v : null))
    .refine(
      (v) => v === null || (Number.isInteger(v) && v >= 1 && v <= 1000),
      "Kapasitas 1–1000 orang.",
    ),
});
type PlaceValues = z.input<typeof placeSchema>;
type PlaceOutput = z.output<typeof placeSchema>;

/** Tambah / ubah mess di daftar master (HR/GA). Koordinat dan kapasitas boleh kosong. */
export function MessPlaceFormDialog({
  place,
  onClose,
}: {
  place?: MessPlace;
  onClose: () => void;
}) {
  const create = useCreateMessPlace();
  const update = useUpdateMessPlace();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<PlaceValues, unknown, PlaceOutput>({
    resolver: zodResolver(placeSchema),
    defaultValues: {
      mess_name: place?.mess_name ?? "",
      city: place?.city ?? "",
      address: place?.address ?? "",
      latitude: place?.latitude ?? null,
      longitude: place?.longitude ?? null,
      capacity: place?.capacity ?? null,
    },
  });

  const onSubmit = async (values: PlaceOutput) => {
    setFormError(null);
    try {
      if (place) await update.mutateAsync({ id: place.mess_id, data: values });
      else await create.mutateAsync(values);
      toast.success(
        place ? "Data mess diperbarui." : "Mess ditambahkan ke daftar.",
      );
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  };

  return (
    <VmsDialog dirty={isDirty}
      open
      title={place ? "Ubah Mess" : "Tambah Mess"}
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="mess-place-form"
        />
      }
    >
      <FormBlock id="mess-place-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}
        <div className="grid grid-cols-2 gap-2">
          <TextField
            label="Nama Mess"
            placeholder="Misal: Mess Duri Sektor Timur"
            maxLength={150}
            error={errors.mess_name?.message}
            {...register("mess_name")}
          />
          <TextField
            label="Kota / Wilayah"
            placeholder="Misal: Duri"
            maxLength={100}
            error={errors.city?.message}
            {...register("city")}
          />
        </div>
        <TextAreaField
          label="Alamat Lengkap"
          placeholder="Jl. Hang Tuah No. 12, Kel. Air Jamban"
          rows={2}
          maxLength={500}
          error={errors.address?.message}
          {...register("address")}
        />
        <div className="grid grid-cols-3 gap-2">
          <TextField
            label="Latitude (opsional)"
            type="number"
            step="any"
            placeholder="1.2845"
            error={errors.latitude?.message}
            {...register("latitude", { valueAsNumber: true })}
          />
          <TextField
            label="Longitude (opsional)"
            type="number"
            step="any"
            placeholder="101.218"
            error={errors.longitude?.message}
            {...register("longitude", { valueAsNumber: true })}
          />
          <TextField
            label="Kapasitas (opsional)"
            type="number"
            min={1}
            max={1000}
            placeholder="10"
            error={errors.capacity?.message}
            {...register("capacity", { valueAsNumber: true })}
          />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
