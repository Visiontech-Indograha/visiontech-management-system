import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import type { LatLng } from "@/lib/geo";
import { useCreateSite } from "@/services/siteService";
import { SiteMapPicker } from "./SiteMapPicker";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";

const coordinate = (min: number, max: number, label: string) =>
  z
    .string()
    .trim()
    .min(1, "Pilih titik di peta, cari alamat, atau isi lintang dan bujur.")
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) >= min && Number(v) <= max, {
      message: `${label} harus angka antara ${min} dan ${max}.`,
    });

const siteSchema = z.object({
  name: z.string().trim().min(1, "Nama lokasi wajib diisi.").max(100, "Nama lokasi maksimal 100 karakter."),
  address: z.string().trim().max(500, "Alamat maksimal 500 karakter."),
  lat: coordinate(-90, 90, "Lintang"),
  lng: coordinate(-180, 180, "Bujur"),
  radius_m: z
    .string()
    .trim()
    .refine((v) => Number.isInteger(Number(v)) && Number(v) >= 10, { message: "Radius minimal 10 meter." })
    .refine((v) => Number(v) <= 5000, { message: "Radius maksimal 5000 meter." }),
});
type SiteValues = z.infer<typeof siteSchema>;

/** Dialog "Tambah lokasi kerja": titik dari peta atau isian manual + radius absensi (POST /sites). */
export function SiteFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateSite();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setValue,
    setError,
    getValues,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<SiteValues>({
    resolver: zodResolver(siteSchema),
    defaultValues: { name: "", address: "", lat: "", lng: "", radius_m: "50" },
  });

  // Titik dari isian (manual) ATAU peta: keduanya satu sumber, jadi penanda dan angka selalu sama.
  const latText = useWatch({ control, name: "lat" });
  const lngText = useWatch({ control, name: "lng" });
  const radiusText = useWatch({ control, name: "radius_m" });
  const a = Number(latText);
  const b = Number(lngText);
  const valid = latText.trim() !== "" && lngText.trim() !== "" && Number.isFinite(a) && Number.isFinite(b) && Math.abs(a) <= 90 && Math.abs(b) <= 180;
  const point = useMemo<LatLng | null>(() => (valid ? [a, b] : null), [valid, a, b]);
  const radius = Number.isFinite(Number(radiusText)) && Number(radiusText) > 0 ? Number(radiusText) : null;

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await create.mutateAsync({
        name: v.name,
        address: v.address || null,
        location: { lat: Number(v.lat), lng: Number(v.lng) },
        radius_m: Number(v.radius_m),
      });
      toast.success("Lokasi kerja ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, ["name", "address"]) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });

  return (
    <VmsDialog dirty={isDirty}
      open
      title="Tambah lokasi kerja"
      onClose={onClose}
      footer={
        <DialogActions onCancel={onClose} busy={isSubmitting} formId="site-form" />
      }
    >
      <FormBlock id="site-form" onSubmit={onSubmit} noValidate>
        <FormErrorText message={formError} />
        <SiteMapPicker
          point={point}
          radius={radius}
          onPick={(p, label) => {
            setValue("lat", p[0].toFixed(6), { shouldValidate: true });
            setValue("lng", p[1].toFixed(6), { shouldValidate: true });
            if (label) {
              setValue("address", label);
              if (!getValues("name").trim()) setValue("name", label.split(",")[0]!.trim(), { shouldValidate: true });
            }
          }}
        />
        <TextField label="Nama lokasi" maxLength={100} error={errors.name?.message} {...register("name")} />
        <TextField label="Alamat" maxLength={500} error={errors.address?.message} {...register("address")} />
        <div className="grid gap-x-3 md:grid-cols-2">
          <TextField label="Lintang (lat)" inputMode="decimal" error={errors.lat?.message} {...register("lat")} />
          <TextField label="Bujur (lng)" inputMode="decimal" error={errors.lng?.message} {...register("lng")} />
        </div>
        <TextField
          label="Radius (meter)"
          inputMode="numeric"
          hint="Jarak maksimal absensi dari titik lokasi."
          error={errors.radius_m?.message}
          {...register("radius_m")}
        />
      </FormBlock>
    </VmsDialog>
  );
}
