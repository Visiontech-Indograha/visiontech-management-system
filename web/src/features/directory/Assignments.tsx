import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SelectField, TextField } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useAssignments, usePromoteEmployee, useUnits, type Employee } from "./api";

/** Riwayat jabatan/penempatan (M2) — riwayat lama tetap tersimpan saat mutasi/promosi. */
export function AssignmentHistory({ employee }: { employee: Employee }) {
  const history = useAssignments(employee.id);
  return (
    <section aria-label="Riwayat jabatan" className="mb-8 max-w-xl">
      <h2 className="mb-3 text-base font-semibold">Riwayat jabatan</h2>
      <div className="rounded-panel border border-line bg-surface shadow-card px-5 py-2 text-sm">
        {history.isPending && <Skeleton className="my-2 h-4 w-2/3" />}
        {history.isError && <p className="py-2 text-danger">Riwayat tidak dapat dimuat.</p>}
        {history.data?.length === 0 && <p className="py-2 text-mist">Belum ada riwayat penempatan.</p>}
        <ol>
          {history.data?.map((a) => (
            <li key={a.id} className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between">
              <span>
                <span className="font-medium">{a.position}</span>
                {a.unit_name && <span className="text-mist"> · {a.unit_name}</span>}
              </span>
              <span className="text-mist">
                {formatDate(a.valid_from)} – {a.valid_to ? formatDate(a.valid_to) : "sekarang"}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

const schema = z.object({
  position: z.string().trim().min(1, "Jabatan wajib diisi."),
  unit_id: z.string().min(1, "Pilih unit."),
  valid_from: z.string().min(1, "Tanggal berlaku wajib diisi."),
});
type Values = z.infer<typeof schema>;

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

/**
 * HR: mutasi/promosi (domain.js PROMOTE). API menolak mutasi lintas unit selama karyawan masih
 * bertugas di SK aktif — pesannya ditampilkan apa adanya.
 */
export function PromoteDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const units = useUnits();
  const promote = usePromoteEmployee(employee.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { position: employee.position, unit_id: employee.unit_id ?? "", valid_from: today() },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await promote.mutateAsync(v);
      toast.success("Penempatan baru berlaku. Riwayat lama tetap tersimpan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });

  return (
    <Dialog
      open
      title="Mutasi / promosi"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="promote-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="promote-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField label="Jabatan" error={errors.position?.message} {...register("position")} />
        <SelectField label="Unit" error={errors.unit_id?.message} {...register("unit_id")}>
          <option value="" disabled>
            {units.isPending ? "Memuat unit..." : "Pilih unit"}
          </option>
          {units.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </SelectField>
        <TextField label="Berlaku mulai" type="date" error={errors.valid_from?.message} {...register("valid_from")} />
      </form>
    </Dialog>
  );
}
