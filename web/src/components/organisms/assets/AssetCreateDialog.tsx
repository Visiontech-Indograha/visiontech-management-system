import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { errorMessage } from "@/lib/errors";
import { toolSchema, vehicleSchema, type ToolValues, type VehicleValues } from "@/schemas/assetSchemas";
import { useCreateTool, useCreateVehicle, type AssetKind } from "@/services/assetService";
import { useDivisions } from "@/services/employeeService";
import { useSites } from "@/services/siteService";
import { AssetFormDialog } from "./AssetFormDialog";

const CATEGORY = { BAJU: "Baju kerja", LAPTOP: "Laptop", SEPATU: "Sepatu safety", BOR: "Bor", TANGGA: "Tangga", LAINNYA: "Lainnya" };
const VEHICLE_TYPE = { Motorcycle: "Motor", Car: "Mobil", Truck: "Truk / pick-up" };

type Place = { office_id: string; division_id: string };

/** Pilihan kantor & divisi pemilik aset (office/division N─1). */
function PlaceFields<T extends Place>({ register, errors, divisionRequired }: {
  register: UseFormRegister<T>;
  errors: FieldErrors<Place>;
  divisionRequired: boolean;
}) {
  const sites = useSites();
  const units = useDivisions();
  const reg = register as unknown as UseFormRegister<Place>;
  return (
    <>
      <SelectField label="Kantor" error={errors.office_id?.message} {...reg("office_id")}>
        <ControlOption value="">Pilih kantor</ControlOption>
        {sites.data?.map((s) => (
          <ControlOption key={s.id} value={s.id}>
            {s.name}
          </ControlOption>
        ))}
      </SelectField>
      <SelectField label={divisionRequired ? "Divisi" : "Divisi (opsional)"} error={errors.division_id?.message} {...reg("division_id")}>
        <ControlOption value="">{divisionRequired ? "Pilih divisi" : "Semua divisi"}</ControlOption>
        {units.data?.map((u) => (
          <ControlOption key={u.id} value={u.id}>
            {u.name}
          </ControlOption>
        ))}
      </SelectField>
    </>
  );
}

function ToolForm({ onClose }: { onClose: () => void }) {
  const create = useCreateTool();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ToolValues>({
    resolver: zodResolver(toolSchema),
    defaultValues: { office_id: "", division_id: "", ownership_type: "SHARED_TOOL", category: "LAINNYA", name: "", tool_code: "" },
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await create.mutateAsync({ ...v, division_id: v.division_id || null });
      toast.success("Alat ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title="Tambah alat" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Kepemilikan" {...register("ownership_type")}>
        <ControlOption value="SHARED_TOOL">Alat bersama proyek (bor, tangga)</ControlOption>
        <ControlOption value="PERSONAL_LOAN">Alat pribadi (baju, sepatu, laptop)</ControlOption>
      </SelectField>
      <SelectField label="Kategori" {...register("category")}>
        {Object.entries(CATEGORY).map(([v, l]) => (
          <ControlOption key={v} value={v}>
            {l}
          </ControlOption>
        ))}
      </SelectField>
      <TextField label="Kode alat" hint="Unik, contoh: TL-BOR-002" error={errors.tool_code?.message} {...register("tool_code")} />
      <TextField label="Nama alat" error={errors.name?.message} {...register("name")} />
      <PlaceFields register={register} errors={errors} divisionRequired={false} />
    </AssetFormDialog>
  );
}

function VehicleForm({ onClose }: { onClose: () => void }) {
  const create = useCreateVehicle();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<VehicleValues>({
    resolver: zodResolver(vehicleSchema),
    defaultValues: { office_id: "", division_id: "", vehicle_type: "Car", name: "", number_plate: "" },
  });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await create.mutateAsync(v);
      toast.success("Kendaraan ditambahkan. Lengkapi STNK/KIR-nya lewat tombol Berkas.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <AssetFormDialog title="Tambah kendaraan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Jenis kendaraan" {...register("vehicle_type")}>
        {Object.entries(VEHICLE_TYPE).map(([v, l]) => (
          <ControlOption key={v} value={v}>
            {l}
          </ControlOption>
        ))}
      </SelectField>
      <TextField label="Nomor polisi" hint="Contoh: BK 1452 ZN" error={errors.number_plate?.message} {...register("number_plate")} />
      <TextField label="Nama kendaraan" error={errors.name?.message} {...register("name")} />
      <PlaceFields register={register} errors={errors} divisionRequired />
    </AssetFormDialog>
  );
}

/** Dialog "Tambah alat" / "Tambah kendaraan" (izin manage:assets). */
export function AssetCreateDialog({ kind, onClose }: { kind: AssetKind; onClose: () => void }) {
  return kind === "TOOL" ? <ToolForm onClose={onClose} /> : <VehicleForm onClose={onClose} />;
}
