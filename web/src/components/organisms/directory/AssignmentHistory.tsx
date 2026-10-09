import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { SelectField, TextField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useAssignments, usePromoteEmployee, useUnits, type Employee } from "@/services/employeeService";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";

/** Riwayat jabatan/penempatan (M2) — riwayat lama tetap tersimpan saat mutasi/promosi. */
export function AssignmentHistory({ employee }: { employee: Employee }) {
  const history = useAssignments(employee.id);
  return (
    <section aria-label="Riwayat jabatan" className="mb-8 max-w-xl">
      <TextBlock as="h2" className="mb-3 text-base font-semibold">Riwayat jabatan</TextBlock>
      <div className="rounded-panel border border-line bg-surface shadow-card px-5 py-2 text-sm">
        {history.isPending && <LoadingBar className="my-2 h-4 w-2/3" />}
        {history.isError && <TextBlock className="py-2 text-danger">Riwayat tidak dapat dimuat.</TextBlock>}
        {history.data?.length === 0 && <TextBlock className="py-2 text-mist">Belum ada riwayat penempatan.</TextBlock>}
        <ListBlock as="ol">
          {history.data?.map((a) => (
            <ListEntry key={a.id} className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between">
              <TextBlock as="span">
                <TextBlock as="span" className="font-medium">{a.position}</TextBlock>
                {a.unit_name && <TextBlock as="span" className="text-mist"> · {a.unit_name}</TextBlock>}
              </TextBlock>
              <TextBlock as="span" className="text-mist">
                {formatDate(a.valid_from)} – {a.valid_to ? formatDate(a.valid_to) : "sekarang"}
              </TextBlock>
            </ListEntry>
          ))}
        </ListBlock>
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
    <VmsDialog
      open
      title="Mutasi / promosi"
      onClose={onClose}
      footer={
        <>
          <ActionButton variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </ActionButton>
          <ActionButton type="submit" form="promote-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </ActionButton>
        </>
      }
    >
      <FormBlock id="promote-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <TextBlock role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </TextBlock>
        )}
        <TextField label="Jabatan" error={errors.position?.message} {...register("position")} />
        <SelectField label="Unit" error={errors.unit_id?.message} {...register("unit_id")}>
          <ControlOption value="" disabled>
            {units.isPending ? "Memuat unit..." : "Pilih unit"}
          </ControlOption>
          {units.data?.map((u) => (
            <ControlOption key={u.id} value={u.id}>
              {u.name}
            </ControlOption>
          ))}
        </SelectField>
        <TextField label="Berlaku mulai" type="date" error={errors.valid_from?.message} {...register("valid_from")} />
      </FormBlock>
    </VmsDialog>
  );
}
