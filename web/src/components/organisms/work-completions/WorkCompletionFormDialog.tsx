import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { useCreateWorkCompletion } from "@/services/workCompletionService";
import { useUserDivisions } from "@/services/employeeService";
import { useClients } from "@/services/clientService";
import { useProjects } from "@/services/projectService";
import { useSession } from "@/stores/sessionStore";

interface FormValues {
  division_id?: string;
  client_id?: string;
  client_name: string;
  project_id?: string;
  project_title: string;
  order_number?: string;
  total_target_unit: number;
  unit_measure: string;
  priority_level: string;
  site_address?: string;
  site_lat?: string | number | null;
  site_lng?: string | number | null;
}

const cleanCoord = (val: unknown, maxVal: number): number | undefined => {
  if (val === undefined || val === null || val === "") return undefined;
  const str = String(val).replace(",", ".").trim();
  let num = Number(str);
  if (Number.isNaN(num)) return undefined;
  if (Math.abs(num) > maxVal) {
    for (const scale of [1e6, 1e7, 1e5]) {
      if (Math.abs(num / scale) <= maxVal) {
        num = num / scale;
        break;
      }
    }
  }
  return Math.abs(num) <= maxVal ? Number(num.toFixed(7)) : undefined;
};

export function WorkCompletionFormDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateWorkCompletion();
  const { me } = useSession();
  const { data: divisions } = useUserDivisions();
  const { data: clients } = useClients(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [isManualInput, setIsManualInput] = useState(false);
  const [clientQuery, setClientQuery] = useState("");

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    defaultValues: {
      division_id: me?.division_id ?? "",
      client_id: "",
      client_name: "",
      project_id: "",
      project_title: "",
      order_number: "",
      total_target_unit: 1,
      unit_measure: "Titik / Unit",
      priority_level: "NORMAL",
      site_address: "",
      site_lat: null,
      site_lng: null,
    },
  });

  const divisionValue = useWatch({ control, name: "division_id" });
  const clientValue = useWatch({ control, name: "client_id" });
  const projectValue = useWatch({ control, name: "project_id" });
  const selectedDivisionId = divisionValue || me?.division_id || undefined;
  const selectedClientId = clientValue || undefined;

  const { data: projects } = useProjects({
    division_id: selectedDivisionId,
    client_id: selectedClientId,
    status: "ONGOING",
  });

  const q = clientQuery.trim().toLowerCase();
  const visibleClients = (clients ?? []).filter(
    (c) => !q || c.name.toLowerCase().includes(q) || c.client_code.toLowerCase().includes(q),
  );

  // Ketika klien dipilih dari dropdown
  const handleClientSelect = (clientId: string) => {
    setValue("client_id", clientId);
    setValue("project_id", "");
    const found = clients?.find((c) => c.client_id === clientId);
    if (found) {
      setValue("client_name", found.name);
    }
  };

  // Ketika proyek master dipilih dari dropdown
  const handleProjectSelect = (projectId: string) => {
    setValue("project_id", projectId);
    const found = projects?.find((p) => p.project_id === projectId);
    if (found) {
      setValue("project_title", found.project_title);
      if (found.spk_number) {
        setValue("order_number", found.spk_number);
      }
      if (found.unit_measure) {
        setValue("unit_measure", found.unit_measure);
      }
      if (found.total_target_qty) {
        setValue("total_target_unit", Number(found.total_target_qty));
      }
    }
  };

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      const parsedLat = cleanCoord(values.site_lat, 90);
      const parsedLng = cleanCoord(values.site_lng, 180);

      if (values.site_lat && parsedLat === undefined) {
        setFormError("Latitude tidak valid. Harus antara -90 dan 90.");
        return;
      }
      if (values.site_lng && parsedLng === undefined) {
        setFormError("Longitude tidak valid. Harus antara -180 dan 180.");
        return;
      }

      await create.mutateAsync({
        division_id: values.division_id || me?.division_id || undefined,
        client_name: values.client_name,
        project_title: values.project_title,
        order_number: values.order_number || undefined,
        total_target_unit: Number(values.total_target_unit),
        unit_measure: values.unit_measure,
        priority_level: values.priority_level,
        site_address: values.site_address || undefined,
        site_lat: parsedLat,
        site_lng: parsedLng,
      });
      toast.success("Pekerjaan klien berhasil dibuat.");
      onClose();
    } catch {
      setFormError("Gagal membuat order proyek klien. Pastikan input terisi dengan benar.");
    }
  };

  return (
    <VmsDialog dirty={isDirty}
      open
      title="Pekerjaan klien baru"
      onClose={onClose}
    >
      <TextBlock className="mb-4 text-sm text-mist">
        Catat pekerjaan dari klien; nanti dibagi ke jadwal tim lapangan.
      </TextBlock>
      {/* Galat formulir (mis. latitude) hilang begitu ada kolom yang diubah, tidak menunggu kirim ulang. */}
      <FormBlock id="work-completion-form" onSubmit={handleSubmit(onSubmit)} onChange={() => setFormError(null)}>
        {formError && <FormErrorText message={formError} />}

        <SelectField
          label="Divisi Penanggung Jawab"
          error={errors.division_id?.message}
          {...register("division_id", {
            required: !me?.division_id ? "Divisi wajib dipilih." : false,
          })}
        >
          <ControlOption value="">-- Pilih Divisi --</ControlOption>
          {(divisions ?? []).map((d) => (
            <ControlOption key={d.id} value={d.id}>
              {d.name}
            </ControlOption>
          ))}
        </SelectField>

        <div className="flex items-center justify-between my-1">
          <TextBlock as="span" className="text-xs text-mist">
            Sumber Data Klien & Proyek:
          </TextBlock>
          <ActionButton
            type="button"
            variant="link"
            size="xs"
            className="text-primary font-medium p-0 h-auto"
            onClick={() => setIsManualInput(!isManualInput)}
          >
            {isManualInput ? "Pilih dari Master Klien/Proyek" : "Ganti ke Input Bebas Manual"}
          </ActionButton>
        </div>

        {!isManualInput && (clients?.length ?? 0) > 0 ? (
          <>
            <TextField
              label="Cari klien"
              placeholder="Ketik kode atau nama klien..."
              value={clientQuery}
              onChange={(e) => setClientQuery(e.target.value)}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <SelectField
                label="Pilih Klien Master"
                value={clientValue ?? ""}
                onChange={(e) => handleClientSelect(e.target.value)}
              >
                <ControlOption value="">-- Pilih Klien Terdaftar --</ControlOption>
                {visibleClients.map((c) => (
                  <ControlOption key={c.client_id} value={c.client_id}>
                    {c.client_code} - {c.name}
                  </ControlOption>
                ))}
              </SelectField>

              <SelectField
                label="Pilih Proyek / SPK Master"
                value={projectValue ?? ""}
                onChange={(e) => handleProjectSelect(e.target.value)}
              >
                <ControlOption value="">-- Pilih Proyek Aktif --</ControlOption>
                {(projects ?? []).map((p) => (
                  <ControlOption key={p.project_id} value={p.project_id}>
                    {p.spk_number} - {p.project_title}
                  </ControlOption>
                ))}
              </SelectField>
            </div>

            <TextField
              label="Nama Klien / Perusahaan"
              placeholder="misal: PT Pertamina EP, PT PLN Persero"
              error={errors.client_name?.message}
              maxLength={150}
              {...register("client_name", { required: "Nama klien wajib diisi." })}
            />

            <TextField
              label="Judul Pekerjaan / Proyek"
              placeholder="misal: Pemasangan 13 Unit CCTV Kilang"
              error={errors.project_title?.message}
              maxLength={255}
              {...register("project_title", { required: "Judul proyek wajib diisi." })}
            />
          </>
        ) : (
          <>
            <TextField
              label="Nama Klien / Perusahaan"
              placeholder="misal: PT Pertamina EP, PT PLN Persero"
              error={errors.client_name?.message}
              maxLength={150}
              {...register("client_name", { required: "Nama klien wajib diisi." })}
            />

            <TextField
              label="Judul Pekerjaan / Proyek"
              placeholder="misal: Pemasangan 13 Unit CCTV Kilang"
              error={errors.project_title?.message}
              maxLength={255}
              {...register("project_title", { required: "Judul proyek wajib diisi." })}
            />
          </>
        )}

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Nomor surat perintah kerja (SPK / PO)"
            placeholder="misal: PO-2026-PTM-001"
            maxLength={50}
            {...register("order_number")}
          />
          <SelectField
            label="Tingkat Prioritas"
            {...register("priority_level")}
          >
            <ControlOption value="NORMAL">Normal</ControlOption>
            <ControlOption value="HIGH">Tinggi (High)</ControlOption>
            <ControlOption value="URGENT">Mendesak (Urgent)</ControlOption>
            <ControlOption value="LOW">Rendah (Low)</ControlOption>
          </SelectField>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Total Target Unit / Volume"
            type="number"
            min={1}
            error={errors.total_target_unit?.message}
            {...register("total_target_unit", { valueAsNumber: true, min: 1 })}
          />
          <TextField
            label="Satuan Unit"
            placeholder="misal: Titik, Unit, Meter, Gardu"
            maxLength={50}
            {...register("unit_measure")}
          />
        </div>

        <TextAreaField
          label="Alamat Site / Lokasi Pelaksanaan (Opsional)"
          placeholder="Alamat lengkap lokasi kerja proyek"
          rows={2}
          {...register("site_address")}
        />

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Latitude Lokasi (Opsional)"
            placeholder="misal: 0.541042 atau -6.2088"
            inputMode="decimal"
            {...register("site_lat")}
          />
          <TextField
            label="Longitude Lokasi (Opsional)"
            placeholder="misal: 101.415331 atau 106.8456"
            inputMode="decimal"
            {...register("site_lng")}
          />
        </div>

        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="work-completion-form"
          submitLabel="Simpan"
          busyLabel="Menyimpan..."
        />
      </FormBlock>
    </VmsDialog>
  );
}
