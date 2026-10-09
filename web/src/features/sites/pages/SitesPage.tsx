import { zodResolver } from "@hookform/resolvers/zod";
import { MapPin } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/atoms/Button";
import { TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/organisms/PageHeader";
import { Skeleton } from "@/components/atoms/Skeleton";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { useCreateSite, useDeleteSite, useSites, type Site } from "../siteService";
import type { LatLng } from "@/features/work-plans/components/PlanLocationCard";
import { SiteMapPicker } from "../components/SiteMapPicker";

/** Master lokasi kerja (geofence absensi): GET/POST/DELETE /sites, izin manage:sites (R-33).
 * PM → lokasi proyek untuk bawahannya (unit ditetapkan server); Finance → lokasi kantor. */
export function SitesPage() {
  const sites = useSites();
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Site | null>(null);

  return (
    <>
      <PageHeader title="Lokasi kerja" action={<Button onClick={() => setAdding(true)}>Tambah lokasi</Button>} />

      {sites.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}
      {sites.isError && (
        <div role="alert" className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <p className="mb-3 text-danger">Lokasi kerja tidak dapat dimuat.</p>
          <Button variant="outline" onClick={() => sites.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {sites.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface shadow-card p-6 text-center">
          <p className="mb-3 text-mist">Belum ada lokasi kerja. Tambahkan lokasi agar absensi bisa memeriksa radius.</p>
          <Button onClick={() => setAdding(true)}>Tambah lokasi</Button>
        </div>
      )}
      {sites.data && sites.data.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {sites.data.map((s) => (
            <li key={s.id} className="flex items-start gap-3 rounded-panel border border-line bg-surface shadow-card p-4">
              <MapPin className="mt-0.5 shrink-0 text-lens" size={20} aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-mist">{s.unit_id ? "Lokasi proyek" : "Lokasi kantor"}</p>
                {s.address && <p className="text-sm text-mist">{s.address}</p>}
                <p className="text-sm text-mist">
                  {s.location.lat.toFixed(6)}, {s.location.lng.toFixed(6)} · radius {s.radius_m} m
                </p>
              </div>
              {s.can_manage && (
                <Button variant="ghost" size="sm" onClick={() => setRemoving(s)} aria-label={`Hapus ${s.name}`}>
                  Hapus
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {adding && <SiteDialog onClose={() => setAdding(false)} />}
      {removing && <DeleteSiteDialog site={removing} onClose={() => setRemoving(null)} />}
    </>
  );
}

const coordinate = (min: number, max: number, label: string) =>
  z
    .string()
    .trim()
    .min(1, `${label} wajib diisi.`)
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) >= min && Number(v) <= max, {
      message: `${label} harus angka antara ${min} dan ${max}.`,
    });

const siteSchema = z.object({
  name: z.string().trim().min(1, "Nama lokasi wajib diisi."),
  address: z.string().trim(),
  lat: coordinate(-90, 90, "Lintang"),
  lng: coordinate(-180, 180, "Bujur"),
  radius_m: z
    .string()
    .trim()
    .refine((v) => Number.isInteger(Number(v)) && Number(v) >= 10, { message: "Radius minimal 10 meter." }),
});
type SiteValues = z.infer<typeof siteSchema>;

function SiteDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateSite();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
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
      setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  });

  return (
    <VmsDialog
      open
      title="Tambah lokasi kerja"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="site-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="site-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
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
        <TextField label="Nama lokasi" error={errors.name?.message} {...register("name")} />
        <TextField label="Alamat" error={errors.address?.message} {...register("address")} />
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
      </form>
    </VmsDialog>
  );
}

function DeleteSiteDialog({ site, onClose }: { site: Site; onClose: () => void }) {
  const remove = useDeleteSite();
  const confirm = async () => {
    try {
      await remove.mutateAsync(site.id);
      toast.success("Lokasi kerja dihapus.");
      onClose();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };
  return (
    <VmsDialog
      open
      title="Hapus lokasi kerja"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={remove.isPending}>
            Batal
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={remove.isPending}>
            {remove.isPending ? "Menghapus..." : "Hapus"}
          </Button>
        </>
      }
    >
      <p>
        Hapus <strong>{site.name}</strong>? Lokasi ini tidak bisa dipakai lagi untuk absensi.
      </p>
    </VmsDialog>
  );
}
