import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { TextField, SelectField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { useClients } from "@/services/clientService";
import { useOffices, useUserDivisions } from "@/services/employeeService";
import { useSaveProject, type Project, type ProjectInput, type ProjectStatus } from "@/services/projectService";
import { useSession } from "@/stores/sessionStore";

export function ProjectFormDialog({
  project,
  onClose,
}: {
  project: Project | null;
  onClose: () => void;
}) {
  const save = useSaveProject(project?.project_id);
  const { me } = useSession();
  const { data: clients } = useClients(true);
  const { data: offices } = useOffices();
  const { data: divisions } = useUserDivisions();

  const [formError, setFormError] = useState<string | null>(null);

  const fallbackDates = useMemo(() => {
    const today = new Date();
    const nextMonth = new Date(today);
    nextMonth.setDate(nextMonth.getDate() + 30);
    return {
      start: today.toISOString().slice(0, 10),
      end: nextMonth.toISOString().slice(0, 10),
    };
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProjectInput>({
    defaultValues: {
      client_id: project?.client_id ?? "",
      office_id: project?.office_id ?? "",
      division_id: project?.division_id ?? me?.division_id ?? "",
      spk_number: project?.spk_number ?? "",
      project_title: project?.project_title ?? "",
      total_target_qty: project?.total_target_qty ? Number(project.total_target_qty) : 1,
      unit_measure: project?.unit_measure ?? "Titik",
      start_date: project?.start_date ? String(project.start_date).slice(0, 10) : fallbackDates.start,
      end_date: project?.end_date ? String(project.end_date).slice(0, 10) : fallbackDates.end,
      status: (project?.status as ProjectStatus) ?? "ONGOING",
    },
  });

  const onSubmit = async (values: ProjectInput) => {
    setFormError(null);
    if (new Date(values.end_date) < new Date(values.start_date)) {
      setFormError("Tanggal selesai tidak boleh sebelum tanggal mulai.");
      return;
    }

    try {
      await save.mutateAsync({
        client_id: values.client_id,
        office_id: values.office_id,
        division_id: values.division_id,
        pm_id: null,
        spk_number: values.spk_number.trim(),
        project_title: values.project_title.trim(),
        total_target_qty: Number(values.total_target_qty),
        unit_measure: values.unit_measure.trim() || "Titik",
        start_date: values.start_date,
        end_date: values.end_date,
        status: values.status,
      });
      toast.success(project ? "Data proyek berhasil diperbarui." : "Proyek baru berhasil didaftarkan.");
      onClose();
    } catch {
      setFormError("Gagal menyimpan data proyek. Pastikan nomor SPK unik dan seluruh kolom wajib terisi.");
    }
  };

  return (
    <VmsDialog
      open
      title={project ? "Ubah data proyek" : "Daftarkan proyek baru"}
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting}
          formId="project-form"
          submitLabel={project ? "Simpan Perubahan" : "Daftarkan Proyek"}
        />
      }
    >
      <TextBlock className="mb-4 text-sm text-mist">
        {project
          ? "Perbarui target deliverable, rentang tanggal SPK, dan status proyek."
          : "Tambahkan proyek induk (SPK) untuk mengelompokkan jadwal rencana kerja harian tim lapangan."}
      </TextBlock>
      <FormBlock id="project-form" onSubmit={handleSubmit(onSubmit)}>
        {formError && <FormErrorText message={formError} />}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <SelectField
            label="Klien Pemberi Kerja"
            error={errors.client_id?.message}
            {...register("client_id", { required: "Klien wajib dipilih." })}
          >
            <ControlOption value="">-- Pilih Klien --</ControlOption>
            {(clients ?? []).map((c) => (
              <ControlOption key={c.client_id} value={c.client_id}>
                {c.client_code} - {c.name}
              </ControlOption>
            ))}
          </SelectField>

          <SelectField
            label="Divisi Kerja"
            error={errors.division_id?.message}
            {...register("division_id", { required: "Divisi wajib dipilih." })}
          >
            <ControlOption value="">-- Pilih Divisi --</ControlOption>
            {(divisions ?? []).map((d) => (
              <ControlOption key={d.id} value={d.id}>
                {d.name}
              </ControlOption>
            ))}
          </SelectField>

          <SelectField
            label="Kantor Cabang / Wilayah"
            error={errors.office_id?.message}
            {...register("office_id", { required: "Kantor wajib dipilih." })}
          >
            <ControlOption value="">-- Pilih Kantor --</ControlOption>
            {(offices ?? []).map((o) => (
              <ControlOption key={o.id} value={o.id}>
                {o.name}
              </ControlOption>
            ))}
          </SelectField>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Nomor Kontrak / SPK"
            placeholder="cth. SPK/VT/TELKOM/2026/001"
            error={errors.spk_number?.message}
            {...register("spk_number", { required: "Nomor SPK wajib diisi." })}
          />

          <TextField
            label="Judul Proyek / Pekerjaan"
            placeholder="cth. Penarikan Kabel Feeder FTTx Riau Segmen 1"
            error={errors.project_title?.message}
            {...register("project_title", { required: "Judul proyek wajib diisi." })}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <TextField
            label="Total Target Kuantitas"
            type="number"
            min="1"
            step="any"
            error={errors.total_target_qty?.message}
            {...register("total_target_qty", {
              required: "Target wajib diisi.",
              min: { value: 1, message: "Minimal target 1." },
            })}
          />

          <TextField
            label="Satuan Ukuran"
            placeholder="cth. Titik, Meter, Tiang, Site"
            error={errors.unit_measure?.message}
            {...register("unit_measure", { required: "Satuan ukuran wajib diisi." })}
          />

          <SelectField
            label="Status Pelaksanaan"
            error={errors.status?.message}
            {...register("status")}
          >
            <ControlOption value="ONGOING">ONGOING (Berjalan)</ControlOption>
            <ControlOption value="DRAFT">DRAFT (Persiapan)</ControlOption>
            <ControlOption value="COMPLETED">COMPLETED (Selesai)</ControlOption>
            <ControlOption value="CANCELLED">CANCELLED (Dibatalkan)</ControlOption>
          </SelectField>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <TextField
            label="Tanggal Mulai"
            type="date"
            error={errors.start_date?.message}
            {...register("start_date", { required: "Tanggal mulai wajib diisi." })}
          />

          <TextField
            label="Tanggal Target Selesai"
            type="date"
            error={errors.end_date?.message}
            {...register("end_date", { required: "Tanggal target selesai wajib diisi." })}
          />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
