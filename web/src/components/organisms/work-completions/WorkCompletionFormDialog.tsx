import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField, TextAreaField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { InlineLink } from "@/components/molecules/Links";
import { koordinatError } from "@/lib/inputRules";
import { useCreateWorkCompletion, useUpdateWorkCompletion, type WorkCompletionOrder } from "@/services/workCompletionService";
import { useUserDivisions } from "@/services/employeeService";
import { useClients } from "@/services/clientService";
import { useProjects } from "@/services/projectService";
import { useSession } from "@/stores/sessionStore";

interface FormValues {
  division_id?: string;
  client_id?: string;
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

/** Koordinat dari isian teks (koma atau titik); kosong menjadi undefined. Batas dicek koordinatError. */
const parseCoord = (val: unknown): number | undefined => {
  const str = String(val ?? "").replace(",", ".").trim();
  return str === "" ? undefined : Number(str);
};

/** Tanpa `order` = buat baru; dengan `order` = ubah (PUT) memakai isian awal dari order. */
export function WorkCompletionFormDialog({ onClose, order }: { onClose: () => void; order?: WorkCompletionOrder }) {
  const editing = !!order;
  const create = useCreateWorkCompletion();
  const update = useUpdateWorkCompletion();
  const { me, activeDivisionId } = useSession();
  const { data: divisions } = useUserDivisions();
  const { data: clients } = useClients(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [clientQuery, setClientQuery] = useState("");

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    defaultValues: order
      ? {
          division_id: order.division_id ?? "",
          client_id: order.client_id ?? "",
          project_id: "",
          project_title: order.project_title,
          order_number: order.order_number ?? "",
          total_target_unit: order.total_target_unit,
          unit_measure: order.unit_measure,
          priority_level: order.priority_level,
          site_address: order.site_address ?? "",
          site_lat: order.site_lat ?? null,
          site_lng: order.site_lng ?? null,
        }
      : {
          division_id: activeDivisionId || me?.division_id || "",
          client_id: "",
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
    // Batas sama dengan API untuk lintang/bujur (-90..90, -180..180); isian di luar batas tidak dikirim.
    if (!values.client_id) return setFormError("Pilih klien dari master klien.");
    const coordErr = koordinatError(String(values.site_lat ?? ""), String(values.site_lng ?? ""));
    if (coordErr) return setFormError(coordErr);
    const parsedLat = parseCoord(values.site_lat);
    const parsedLng = parseCoord(values.site_lng);
    try {
      if (order) {
        await update.mutateAsync({
          id: order.completion_id,
          payload: {
            client_id: values.client_id || null,
            project_title: values.project_title,
            order_number: values.order_number || null,
            total_target_unit: Number(values.total_target_unit),
            unit_measure: values.unit_measure,
            priority_level: values.priority_level,
            site_address: values.site_address || null,
            site_lat: parsedLat ?? null,
            site_lng: parsedLng ?? null,
          },
        });
        toast.success("Pekerjaan klien diperbarui.");
      } else {
        await create.mutateAsync({
          division_id: values.division_id || me?.division_id || undefined,
          client_id: values.client_id || null,
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
      }
      onClose();
    } catch {
      setFormError(editing ? "Gagal memperbarui pekerjaan klien. Periksa input." : "Gagal membuat order proyek klien. Pastikan input terisi dengan benar.");
    }
  };

  return (
    <VmsDialog dirty={isDirty}
      open
      title={editing ? "Ubah pekerjaan klien" : "Pekerjaan klien baru"}
      onClose={onClose}
    >
      <TextBlock className="mb-4 text-sm text-mist">
        Catat pekerjaan dari klien; nanti dibagi ke jadwal tim lapangan.
      </TextBlock>
      {/* Galat formulir (mis. latitude) hilang begitu ada kolom yang diubah, tidak menunggu kirim ulang. */}
      <FormBlock id="work-completion-form" onSubmit={handleSubmit(onSubmit)} onChange={() => setFormError(null)}>
        {formError && <FormErrorText message={formError} />}

        {!editing && (
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
        )}

        {(clients?.length ?? 0) > 0 ? (
          <>
            <TextField
              label="Cari klien"
              placeholder="Cari awal nama atau kode klien..."
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
            {(projects ?? []).length === 0 && (
              <TextBlock className="rounded-control border border-dashed border-line p-3 text-sm text-mist">
                {clientValue ? (
                  <>
                    <TextBlock as="span">Klien ini belum punya SPK aktif.</TextBlock>{" "}
                    <InlineLink to={`/projects?client_id=${clientValue}`} className="text-primary underline">
                      Buat SPK untuk klien ini
                    </InlineLink>
                  </>
                ) : (
                  "Belum ada SPK aktif di divisi ini. Pilih klien atau isi manual."
                )}
              </TextBlock>
            )}

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
            <TextBlock className="rounded-control border border-dashed border-line p-3 text-sm text-mist">
              Belum ada klien di master. Tambahkan dulu klien di menu Klien, lalu buat pekerjaannya.
            </TextBlock>

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
