import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { useCorrection } from "./api";

type Errors = Record<string, string>;

/** Koreksi absen manual (TL: anggota timnya; SA: siapa pun). Maks. 7 hari ke belakang. */
export function CorrectionDialog({ onClose }: { onClose: () => void }) {
  const employees = useQuery({
    queryKey: ["employees-picker"],
    queryFn: async () =>
      (await api.get<components["schemas"]["Page_EmployeeOut_"]>("/employees", { params: { page_size: 100 } })).data.items,
  });
  const correct = useCorrection();
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const today = new Date().toISOString().slice(0, 10);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const val = (k: string) => String(f.get(k) ?? "").trim() || undefined;
    setErrors({});
    setFormError(null);
    try {
      await correct.mutateAsync({
        user_id: val("user_id"),
        attendance_date: val("attendance_date"),
        manual_reason: val("manual_reason") ?? "",
        latitude: val("latitude"),
        longitude: val("longitude"),
        note: val("note"),
      });
      toast.success("Koreksi absen tercatat.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <Dialog
      open
      title="Koreksi absen"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="correction-form" disabled={correct.isPending}>
            Simpan koreksi
          </Button>
        </>
      }
    >
      <form id="correction-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <SelectField name="user_id" label="Karyawan" defaultValue="" error={errors.user_id}>
          <option value="" disabled>
            Pilih karyawan...
          </option>
          {employees.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name}
            </option>
          ))}
        </SelectField>
        <TextField name="attendance_date" label="Tanggal" type="date" defaultValue={today} max={today} error={errors.attendance_date} hint="Maksimal 7 hari ke belakang. Tidak dapat menimpa absen yang sudah ada." />
        <TextField name="manual_reason" label="Alasan" error={errors.manual_reason} />
        <TextField name="latitude" label="Latitude (opsional)" type="number" step="any" error={errors.latitude} />
        <TextField name="longitude" label="Longitude (opsional)" type="number" step="any" error={errors.longitude} />
        <TextField name="note" label="Catatan (opsional)" error={errors.note} />
      </form>
    </Dialog>
  );
}
