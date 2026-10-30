import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DialogCancelButton } from "@/components/molecules/DialogActions";
import { TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { SiteMapPicker } from "@/components/organisms/sites/SiteMapPicker";
import { errorMessage } from "@/lib/errors";
import { useUpdateDailyPlanLocation, type DailyPlan } from "@/services/dailyPlanService";

/**
 * Ubah lokasi jadwal DISETUJUI yang belum dimulai (PM/OM) tanpa mengembalikannya ke draf.
 * Aturan sama dengan API: nama 2-150 karakter, koordinat lengkap, radius 10-5000 m.
 */
export function DailyPlanLocationForm({ plan, onDone, onCancel }: {
  plan: DailyPlan;
  onDone: () => void;
  onCancel: () => void;
}) {
  const update = useUpdateDailyPlanLocation(plan.daily_plan_id);
  const [name, setName] = useState(plan.site_name ?? "");
  const [lat, setLat] = useState(plan.site_lat != null ? String(plan.site_lat) : "");
  const [lng, setLng] = useState(plan.site_lng != null ? String(plan.site_lng) : "");
  const [radius, setRadius] = useState(String(plan.attendance_radius_m ?? 150));
  const [error, setError] = useState<string | null>(null);

  const latN = Number(lat);
  const lngN = Number(lng);
  const point = lat.trim() && lng.trim() && Number.isFinite(latN) && Number.isFinite(lngN) ? ([latN, lngN] as [number, number]) : null;
  const radiusN = Number(radius);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (name.trim().length < 2) return setError("Nama lokasi minimal 2 karakter.");
    if (!lat.trim() || !lng.trim() || !Number.isFinite(latN) || !Number.isFinite(lngN)) return setError("Isi kedua koordinat dengan angka.");
    if (Math.abs(latN) > 90 || Math.abs(lngN) > 180) return setError("Koordinat tidak valid (latitude -90..90, longitude -180..180).");
    if (!Number.isInteger(radiusN) || radiusN < 10 || radiusN > 5000) return setError("Radius absen 10 sampai 5000 meter.");
    setError(null);
    try {
      await update.mutateAsync({ site_name: name.trim(), site_lat: latN, site_lng: lngN, attendance_radius_m: radiusN });
      toast.success("Lokasi jadwal diubah. Jadwal tetap disetujui.");
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <FormBlock onSubmit={submit} aria-label="Ubah lokasi jadwal" className="space-y-2" noValidate>
      <SiteMapPicker point={point} radius={Number.isFinite(radiusN) && radiusN > 0 ? radiusN : null}
        onPick={(p, label) => {
          setLat(p[0].toFixed(7));
          setLng(p[1].toFixed(7));
          if (label) setName(label.split(",")[0]!.trim());
        }} />
      <TextField label="Nama lokasi" value={name} onChange={(e) => setName(e.target.value)} />
      <div className="grid gap-x-3 md:grid-cols-3">
        <TextField label="Lintang (lat)" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} />
        <TextField label="Bujur (lng)" inputMode="decimal" value={lng} onChange={(e) => setLng(e.target.value)} />
        <TextField label="Radius absen (m)" inputMode="numeric" value={radius} onChange={(e) => setRadius(e.target.value)} />
      </div>
      <FormErrorText message={error} />
      <div className="flex gap-2">
        <ActionButton type="submit" size="sm" disabled={update.isPending}>Simpan lokasi</ActionButton>
        <DialogCancelButton onCancel={onCancel} disabled={update.isPending} />
      </div>
    </FormBlock>
  );
}
