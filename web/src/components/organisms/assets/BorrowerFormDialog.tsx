import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { borrowerSchema, type BorrowerValues } from "@/schemas/assetSchemas";
import { useCreateBorrower, useUpdateBorrower, type Borrower } from "@/services/assetService";
import { useSites } from "@/services/siteService";
import { AssetFormDialog } from "./AssetFormDialog";

const KNOWN = ["office_id", "nama", "instansi", "kontak"] as const;

const defaultsOf = (b?: Borrower): BorrowerValues => ({
  office_id: b?.office_id ?? "",
  nama: b?.nama ?? "",
  instansi: b?.instansi ?? "",
  kontak: b?.kontak ?? "",
});

/** Tambah atau ubah penerima luar perusahaan (klien sewa, subkontraktor). Data seminimal mungkin. */
export function BorrowerFormDialog({ borrower, onClose }: { borrower?: Borrower; onClose: () => void }) {
  const create = useCreateBorrower();
  const update = useUpdateBorrower();
  const sites = useSites();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<BorrowerValues>({
    resolver: zodResolver(borrowerSchema),
    defaultValues: defaultsOf(borrower),
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await save(v);
      toast.success(borrower ? "Data penerima disimpan." : "Penerima ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(applyFieldErrors(err, setError, KNOWN) ? "Periksa kolom yang ditandai." : errorMessage(err));
    }
  });
  const save = async (v: BorrowerValues) => {
    const rest = { nama: v.nama, instansi: v.instansi || null, kontak: v.kontak || null };
    if (borrower) await update.mutateAsync({ id: borrower.borrower_id, body: rest });
    else await create.mutateAsync({ office_id: v.office_id, ...rest });
  };
  return (
    <AssetFormDialog title={borrower ? "Ubah penerima" : "Tambah penerima"} submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      {!borrower && (
        <SelectField label="Kantor" error={errors.office_id?.message} {...register("office_id")}>
          <ControlOption value="">Pilih kantor</ControlOption>
          {sites.data?.map((s) => <ControlOption key={s.id} value={s.id}>{s.name}</ControlOption>)}
        </SelectField>
      )}
      <TextField label="Nama penerima" maxLength={150} error={errors.nama?.message} {...register("nama")} />
      <TextField label="Perusahaan atau instansi (opsional)" maxLength={150} error={errors.instansi?.message} {...register("instansi")} />
      <TextField label="Kontak (opsional)" maxLength={100} hint="Nomor HP atau email. Tanpa KTP atau alamat." error={errors.kontak?.message} {...register("kontak")} />
    </AssetFormDialog>
  );
}
