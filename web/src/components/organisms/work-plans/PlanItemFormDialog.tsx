/**
 * web/src/components/organisms/work-plans/PlanItemFormDialog.tsx
 * Dialog modal untuk Menambah atau Mengubah Butir Tugas / Slot Multi-Task (work_plan_item):
 * - Judul tugas (title)
 * - Jenis pekerjaan (work_type_id)
 * - Kaitan order klien (completion_id, opsional)
 * - Target unit / volume (target_qty)
 * - Capaian realisasi & progres (completed_qty, progress_percent)
 * - Jam slot (start_time, end_time)
 * - Titik lokasi spesifik (location_name)
 * - Penugasan teknisi lapangan (assigned_employee_ids)
 * - Status tugas (status)
 */

import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock, ControlLabel, ControlInput, ControlSelect, ControlOption } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import {
  useCreatePlanItemV2,
  useUpdatePlanItemV2,
  type PlanItemV2Value,
  type TeamMemberOption,
  type WorkCompletionOption,
  type WorkTypeOption,
} from "@/services/workPlanV2Service";

interface PlanItemFormDialogProps {
  open: boolean;
  onClose: () => void;
  dailyPlanId: string;
  weeklyPlanId?: string;
  initialData?: Partial<PlanItemV2Value> | null;
  workTypes?: WorkTypeOption[];
  completions?: WorkCompletionOption[];
  teamMembers?: TeamMemberOption[];
  onSaved?: () => void;
}

export const PlanItemFormDialog: React.FC<PlanItemFormDialogProps> = ({
  open,
  onClose,
  dailyPlanId,
  weeklyPlanId,
  initialData,
  workTypes = [],
  completions = [],
  teamMembers = [],
  onSaved,
}) => {
  const isEditing = Boolean(initialData?.item_id);

  const [title, setTitle] = useState("");
  const [workTypeId, setWorkTypeId] = useState("");
  const [completionId, setCompletionId] = useState("");
  const [targetQty, setTargetQty] = useState("1.00");
  const [completedQty, setCompletedQty] = useState("0.00");
  const [progressPercent, setProgressPercent] = useState("0");
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("12:00");
  const [locationName, setLocationName] = useState("");
  const [taskPhase, setTaskPhase] = useState<PlanItemV2Value["task_phase"]>("MAIN_INSTALLATION");
  const [isMainDeliverable, setIsMainDeliverable] = useState<boolean>(true);
  const [assignedEmployeeIds, setAssignedEmployeeIds] = useState<string[]>([]);
  const [status, setStatus] = useState<PlanItemV2Value["status"]>("PENDING");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createMut = useCreatePlanItemV2();
  const updateMut = useUpdatePlanItemV2();
  const isPending = createMut.isPending || updateMut.isPending;

  useEffect(() => {
    if (initialData) {
      setTitle(initialData.title || "");
      setWorkTypeId(initialData.work_type_id || (workTypes[0]?.work_type_id ?? ""));
      setCompletionId(initialData.completion_id || "");
      setTargetQty(String(initialData.target_qty ?? "1.00"));
      setCompletedQty(String(initialData.completed_qty ?? "0.00"));
      setProgressPercent(String(initialData.progress_percent ?? "0"));
      setStartTime(initialData.start_time ? initialData.start_time.slice(0, 5) : "08:00");
      setEndTime(initialData.end_time ? initialData.end_time.slice(0, 5) : "12:00");
      setLocationName(initialData.location_name || "");
      setTaskPhase(initialData.task_phase || "MAIN_INSTALLATION");
      setIsMainDeliverable(initialData.is_main_deliverable !== undefined ? initialData.is_main_deliverable : true);
      setAssignedEmployeeIds(initialData.assigned_employee_ids || []);
      setStatus(initialData.status || "PENDING");
    } else {
      setTitle("");
      setWorkTypeId(workTypes[0]?.work_type_id ?? "");
      setCompletionId("");
      setTargetQty("1.00");
      setCompletedQty("0.00");
      setProgressPercent("0");
      setStartTime("08:00");
      setEndTime("12:00");
      setLocationName("");
      setTaskPhase("MAIN_INSTALLATION");
      setIsMainDeliverable(true);
      setAssignedEmployeeIds([]);
      setStatus("PENDING");
    }
    setErrorMsg(null);
  }, [initialData, open, workTypes]);

  const toggleEmployee = (empId: string) => {
    setAssignedEmployeeIds((prev) =>
      prev.includes(empId) ? prev.filter((id) => id !== empId) : [...prev, empId]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!title.trim()) {
      setErrorMsg("Judul tugas kerja wajib diisi.");
      return;
    }
    if (!workTypeId) {
      setErrorMsg("Jenis pekerjaan wajib dipilih.");
      return;
    }
    const targetVal = parseFloat(targetQty);
    if (isNaN(targetVal) || targetVal <= 0) {
      setErrorMsg("Target volume pekerjaan harus lebih besar dari 0.");
      return;
    }

    const payload: PlanItemV2Value = {
      daily_plan_id: dailyPlanId,
      weekly_plan_id: weeklyPlanId,
      title: title.trim(),
      task_phase: taskPhase,
      is_main_deliverable: isMainDeliverable,
      work_type_id: workTypeId,
      completion_id: completionId ? completionId : null,
      target_qty: targetVal,
      completed_qty: parseFloat(completedQty) || 0,
      progress_percent: parseFloat(progressPercent) || 0,
      start_time: startTime.length === 5 ? `${startTime}:00` : startTime,
      end_time: endTime.length === 5 ? `${endTime}:00` : endTime,
      location_name: locationName.trim() || undefined,
      assigned_employee_ids: assignedEmployeeIds,
      status,
      rollover_approval_status: initialData?.rollover_approval_status || "NONE",
      delay_reason: initialData?.delay_reason || null,
    };

    try {
      if (isEditing && initialData?.item_id) {
        await updateMut.mutateAsync({
          id: initialData.item_id,
          data: payload,
        });
        toast.success("Tugas kerja berhasil diperbarui!");
      } else {
        await createMut.mutateAsync(payload);
        toast.success("Tugas kerja baru berhasil ditambahkan!");
      }
      onSaved?.();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal menyimpan tugas kerja.";
      setErrorMsg(msg);
      toast.error(msg);
    }
  };

  return (
    <VmsDialog
      open={open}
      title={isEditing ? "Ubah Butir Tugas / Slot Kerja" : "Tambah Tugas Baru ke Hari Ini"}
      onClose={onClose}
      footer={
        <div className="flex w-full items-center justify-end gap-2">
          <ActionButton type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Batal
          </ActionButton>
          <ActionButton type="button" variant="default" onClick={handleSave} disabled={isPending}>
            {isPending ? "Menyimpan..." : isEditing ? "Perbarui Tugas" : "Tambah Tugas"}
          </ActionButton>
        </div>
      }
    >
      <form onSubmit={handleSave} className="space-y-4">
        <FormErrorText message={errorMsg} />

        <FormBlock>
          <ControlLabel htmlFor="item_title">Judul Tugas / Rincian Pekerjaan</ControlLabel>
          <ControlInput
            id="item_title"
            type="text"
            placeholder="Contoh: Penarikan Drop Core 12 Core Sektor Timur"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </FormBlock>

        <FormBlock>
          <ControlLabel htmlFor="item_work_type">Jenis Pekerjaan (Work Type)</ControlLabel>
          <ControlSelect
            id="item_work_type"
            value={workTypeId}
            onChange={(e) => setWorkTypeId(e.target.value)}
            required
          >
            <ControlOption value="">-- Pilih Jenis Pekerjaan --</ControlOption>
            {workTypes.map((wt) => (
              <ControlOption key={wt.work_type_id} value={wt.work_type_id}>
                {wt.name} {wt.description ? `- ${wt.description}` : ""}
              </ControlOption>
            ))}
          </ControlSelect>
        </FormBlock>

        <FormBlock>
          <ControlLabel htmlFor="item_completion">Kaitan Order Klien / Proyek (Opsional)</ControlLabel>
          <ControlSelect
            id="item_completion"
            value={completionId}
            onChange={(e) => setCompletionId(e.target.value)}
          >
            <ControlOption value="">-- Tidak Terkait Order Induk Spesifik --</ControlOption>
            {completions.map((c) => (
              <ControlOption key={c.completion_id} value={c.completion_id}>
                [{c.client_name}] {c.project_title} {c.order_number ? `(${c.order_number})` : ""}
              </ControlOption>
            ))}
          </ControlSelect>
        </FormBlock>

        <div className="grid grid-cols-2 gap-3">
          <FormBlock>
            <ControlLabel htmlFor="item_task_phase">Tahap Pekerjaan (Multi-Week Phase)</ControlLabel>
            <ControlSelect
              id="item_task_phase"
              value={taskPhase}
              onChange={(e) => setTaskPhase(e.target.value as PlanItemV2Value["task_phase"])}
            >
              <ControlOption value="SURVEY">1. Survei Lapangan & Jalur</ControlOption>
              <ControlOption value="PREPARATION">2. Persiapan (Skafolding / Galian)</ControlOption>
              <ControlOption value="MAIN_INSTALLATION">3. Instalasi Fisik Utama</ControlOption>
              <ControlOption value="TESTING_COMMISSIONING">4. Pengujian & Komisioning</ControlOption>
              <ControlOption value="FINISHING">5. Finishing & Dokumentasi</ControlOption>
            </ControlSelect>
          </FormBlock>

          <FormBlock>
            <ControlLabel htmlFor="item_is_deliverable">Klasifikasi Deliverable</ControlLabel>
            <ControlSelect
              id="item_is_deliverable"
              value={isMainDeliverable ? "true" : "false"}
              onChange={(e) => setIsMainDeliverable(e.target.value === "true")}
            >
              <ControlOption value="true">Deliverable Utama (Masuk BAST)</ControlOption>
              <ControlOption value="false">Pekerjaan Pendukung (Non-BAST)</ControlOption>
            </ControlSelect>
          </FormBlock>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <FormBlock>
            <ControlLabel htmlFor="item_target_qty">Target Unit / Volume</ControlLabel>
            <ControlInput
              id="item_target_qty"
              type="number"
              step="any"
              min="0.01"
              value={targetQty}
              onChange={(e) => setTargetQty(e.target.value)}
              required
            />
          </FormBlock>

          <FormBlock>
            <ControlLabel htmlFor="item_status">Status Tugas</ControlLabel>
            <ControlSelect
              id="item_status"
              value={status}
              onChange={(e) => setStatus(e.target.value as PlanItemV2Value["status"])}
            >
              <ControlOption value="PENDING">PENDING</ControlOption>
              <ControlOption value="IN_PROGRESS">IN_PROGRESS</ControlOption>
              <ControlOption value="COMPLETED">COMPLETED</ControlOption>
              <ControlOption value="DONE">DONE</ControlOption>
              <ControlOption value="DELAYED">DELAYED</ControlOption>
              <ControlOption value="CANCELLED">CANCELLED</ControlOption>
            </ControlSelect>
          </FormBlock>
        </div>

        {isEditing && (
          <div className="grid grid-cols-2 gap-3 rounded-panel border border-line bg-canvas p-3">
            <FormBlock>
              <ControlLabel htmlFor="item_completed_qty">Realisasi Aktual</ControlLabel>
              <ControlInput
                id="item_completed_qty"
                type="number"
                step="any"
                min="0"
                value={completedQty}
                onChange={(e) => setCompletedQty(e.target.value)}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="item_progress_percent">Progres (%)</ControlLabel>
              <ControlInput
                id="item_progress_percent"
                type="number"
                min="0"
                max="100"
                value={progressPercent}
                onChange={(e) => setProgressPercent(e.target.value)}
              />
            </FormBlock>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <FormBlock>
            <ControlLabel htmlFor="item_start_time">Jam Mulai Slot</ControlLabel>
            <ControlInput
              id="item_start_time"
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </FormBlock>

          <FormBlock>
            <ControlLabel htmlFor="item_end_time">Jam Selesai Slot</ControlLabel>
            <ControlInput
              id="item_end_time"
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </FormBlock>
        </div>

        <FormBlock>
          <ControlLabel htmlFor="item_location">Titik / Posisi Spesifik (Opsional)</ControlLabel>
          <ControlInput
            id="item_location"
            type="text"
            placeholder="Contoh: Tiang ODP-MDN-04 / Ruang Server Lt 2"
            value={locationName}
            onChange={(e) => setLocationName(e.target.value)}
          />
        </FormBlock>

        {teamMembers.length > 0 && (
          <FormBlock>
            <ControlLabel>Penugasan Teknisi Lapangan</ControlLabel>
            <div className="mt-2 flex flex-wrap gap-2">
              {teamMembers.map((tm) => {
                const isSelected = assignedEmployeeIds.includes(tm.employee_id);
                return (
                  <button
                    key={tm.employee_id}
                    type="button"
                    onClick={() => toggleEmployee(tm.employee_id)}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                      isSelected
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-line bg-surface text-mist hover:text-ink"
                    }`}
                  >
                    <span>{isSelected ? "✓" : "+"}</span>
                    <span>{tm.full_name}</span>
                    <span className="text-[10px] opacity-75">({tm.position})</span>
                  </button>
                );
              })}
            </div>
            <TextBlock className="mt-1 text-xs text-mist">
              Klik nama teknisi untuk menandai siapa saja yang bertugas pada slot item ini.
            </TextBlock>
          </FormBlock>
        )}
      </form>
    </VmsDialog>
  );
};
