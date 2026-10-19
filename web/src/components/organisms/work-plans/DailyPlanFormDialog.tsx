/**
 * web/src/components/organisms/work-plans/DailyPlanFormDialog.tsx
 * Dialog modal untuk Menambah atau Mengubah Rencana Harian (work_plan_daily):
 * - Tanggal kerja (work_date)
 * - Nama site / lokasi kerja (site_name) dengan preset kantor/site
 * - Koordinat GPS (site_lat, site_lng)
 * - Radius absensi presensi (attendance_radius_m, default 150m)
 * - Jam kerja (clock_in_time, clock_out_time)
 * - Status harian (SCHEDULED, ONGOING, COMPLETED, HOLIDAY)
 */

import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock, ControlLabel, ControlInput, ControlSelect, ControlOption } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import {
  useCreateDailyPlanV2,
  useUpdateDailyPlanV2,
  type DailyPlanV2Value,
  type OfficeSiteOption,
} from "@/services/workPlanV2Service";

interface DailyPlanFormDialogProps {
  open: boolean;
  onClose: () => void;
  weeklyPlanId: string;
  initialData?: Partial<DailyPlanV2Value> | null;
  offices?: OfficeSiteOption[];
  onSaved?: () => void;
}

export const DailyPlanFormDialog: React.FC<DailyPlanFormDialogProps> = ({
  open,
  onClose,
  weeklyPlanId,
  initialData,
  offices = [],
  onSaved,
}) => {
  const isEditing = Boolean(initialData?.daily_plan_id);

  const [workDate, setWorkDate] = useState("");
  const [siteName, setSiteName] = useState("");
  const [siteLat, setSiteLat] = useState("3.5952");
  const [siteLng, setSiteLng] = useState("98.6722");
  const [attendanceRadiusM, setAttendanceRadiusM] = useState("150");
  const [clockInTime, setClockInTime] = useState("08:00");
  const [clockOutTime, setClockOutTime] = useState("17:00");
  const [status, setStatus] = useState<DailyPlanV2Value["status"]>("SCHEDULED");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createMut = useCreateDailyPlanV2();
  const updateMut = useUpdateDailyPlanV2();
  const isPending = createMut.isPending || updateMut.isPending;

  useEffect(() => {
    if (initialData) {
      setWorkDate(initialData.work_date || "");
      setSiteName(initialData.site_name || "");
      setSiteLat(String(initialData.site_lat ?? "3.5952"));
      setSiteLng(String(initialData.site_lng ?? "98.6722"));
      setAttendanceRadiusM(String(initialData.attendance_radius_m ?? "150"));
      setClockInTime(initialData.clock_in_time ? initialData.clock_in_time.slice(0, 5) : "08:00");
      setClockOutTime(initialData.clock_out_time ? initialData.clock_out_time.slice(0, 5) : "17:00");
      setStatus(initialData.status || "SCHEDULED");
    } else {
      setWorkDate(new Date().toISOString().slice(0, 10));
      setSiteName("");
      setSiteLat("3.5952");
      setSiteLng("98.6722");
      setAttendanceRadiusM("150");
      setClockInTime("08:00");
      setClockOutTime("17:00");
      setStatus("SCHEDULED");
    }
    setErrorMsg(null);
  }, [initialData, open]);

  const handleSelectPresetOffice = (officeId: string) => {
    const found = offices.find((o) => o.office_id === officeId);
    if (found) {
      setSiteName(found.name);
      setSiteLat(String(found.latitude));
      setSiteLng(String(found.longitude));
      if (found.radius_m) setAttendanceRadiusM(String(found.radius_m));
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!workDate) {
      setErrorMsg("Tanggal kerja wajib diisi.");
      return;
    }
    if (!siteName.trim()) {
      setErrorMsg("Nama site/lokasi kerja wajib diisi.");
      return;
    }

    const payload: DailyPlanV2Value = {
      weekly_plan_id: weeklyPlanId,
      work_date: workDate,
      site_name: siteName.trim(),
      site_lat: parseFloat(siteLat) || 0,
      site_lng: parseFloat(siteLng) || 0,
      attendance_radius_m: parseInt(attendanceRadiusM, 10) || 150,
      clock_in_time: clockInTime.length === 5 ? `${clockInTime}:00` : clockInTime,
      clock_out_time: clockOutTime.length === 5 ? `${clockOutTime}:00` : clockOutTime,
      status,
      is_holiday: status === "HOLIDAY",
      items: initialData?.items || [],
    };

    try {
      if (isEditing && initialData?.daily_plan_id) {
        await updateMut.mutateAsync({
          id: initialData.daily_plan_id,
          data: payload,
        });
        toast.success("Hari kerja berhasil diperbarui!");
      } else {
        await createMut.mutateAsync(payload);
        toast.success("Hari kerja baru berhasil ditambahkan!");
      }
      onSaved?.();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal menyimpan hari kerja.";
      setErrorMsg(msg);
      toast.error(msg);
    }
  };

  return (
    <VmsDialog
      open={open}
      title={isEditing ? "Ubah Rencana Harian" : "Tambah Hari Kerja Baru"}
      onClose={onClose}
      footer={
        <div className="flex w-full items-center justify-end gap-2">
          <ActionButton type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Batal
          </ActionButton>
          <ActionButton type="button" variant="default" onClick={handleSave} disabled={isPending}>
            {isPending ? "Menyimpan..." : isEditing ? "Perbarui Hari" : "Tambah Hari"}
          </ActionButton>
        </div>
      }
    >
      <form onSubmit={handleSave} className="space-y-4">
        <FormErrorText message={errorMsg} />

        <FormBlock>
          <ControlLabel htmlFor="daily_work_date">Tanggal Kerja</ControlLabel>
          <ControlInput
            id="daily_work_date"
            type="date"
            value={workDate}
            onChange={(e) => setWorkDate(e.target.value)}
            required
          />
        </FormBlock>

        {offices.length > 0 && (
          <FormBlock>
            <ControlLabel htmlFor="office_preset">Preset Lokasi Kantor / Site</ControlLabel>
            <ControlSelect
              id="office_preset"
              defaultValue=""
              onChange={(e) => handleSelectPresetOffice(e.target.value)}
            >
              <ControlOption value="">-- Pilih preset kantor/site (opsional) --</ControlOption>
              {offices.map((o) => (
                <ControlOption key={o.office_id} value={o.office_id}>
                  {o.name} {o.address ? `(${o.address})` : ""}
                </ControlOption>
              ))}
            </ControlSelect>
          </FormBlock>
        )}

        <FormBlock>
          <ControlLabel htmlFor="daily_site_name">Nama Site / Lokasi Kerja</ControlLabel>
          <ControlInput
            id="daily_site_name"
            type="text"
            placeholder="Contoh: Site STO Medan Kota / Cluster Tanjung Morawa"
            value={siteName}
            onChange={(e) => setSiteName(e.target.value)}
            required
          />
        </FormBlock>

        <div className="grid grid-cols-2 gap-3">
          <FormBlock>
            <ControlLabel htmlFor="daily_site_lat">Latitude GPS</ControlLabel>
            <ControlInput
              id="daily_site_lat"
              type="number"
              step="any"
              value={siteLat}
              onChange={(e) => setSiteLat(e.target.value)}
              required
            />
          </FormBlock>

          <FormBlock>
            <ControlLabel htmlFor="daily_site_lng">Longitude GPS</ControlLabel>
            <ControlInput
              id="daily_site_lng"
              type="number"
              step="any"
              value={siteLng}
              onChange={(e) => setSiteLng(e.target.value)}
              required
            />
          </FormBlock>
        </div>

        <FormBlock>
          <ControlLabel htmlFor="daily_radius">Radius Absensi Presensi (Meter)</ControlLabel>
          <ControlInput
            id="daily_radius"
            type="number"
            min={10}
            max={50000}
            value={attendanceRadiusM}
            onChange={(e) => setAttendanceRadiusM(e.target.value)}
            required
          />
          <TextBlock className="mt-1 text-xs text-mist">
            Default 150 meter. Gunakan 15000 meter bila tugas proyek berstatus luar kota/area luas.
          </TextBlock>
        </FormBlock>

        <div className="grid grid-cols-2 gap-3">
          <FormBlock>
            <ControlLabel htmlFor="daily_clock_in">Jam Masuk (Jadwal)</ControlLabel>
            <ControlInput
              id="daily_clock_in"
              type="time"
              value={clockInTime}
              onChange={(e) => setClockInTime(e.target.value)}
              required
            />
          </FormBlock>

          <FormBlock>
            <ControlLabel htmlFor="daily_clock_out">Jam Pulang (Jadwal)</ControlLabel>
            <ControlInput
              id="daily_clock_out"
              type="time"
              value={clockOutTime}
              onChange={(e) => setClockOutTime(e.target.value)}
              required
            />
          </FormBlock>
        </div>

        <FormBlock>
          <ControlLabel htmlFor="daily_status">Status Hari Kerja</ControlLabel>
          <ControlSelect
            id="daily_status"
            value={status}
            onChange={(e) => setStatus(e.target.value as DailyPlanV2Value["status"])}
          >
            <ControlOption value="SCHEDULED">SCHEDULED (Terjadwal)</ControlOption>
            <ControlOption value="ONGOING">ONGOING (Sedang Berjalan)</ControlOption>
            <ControlOption value="PARTIAL">PARTIAL (Selesai Sebagian)</ControlOption>
            <ControlOption value="COMPLETED">COMPLETED (Selesai)</ControlOption>
            <ControlOption value="HOLIDAY">HOLIDAY (Hari Libur)</ControlOption>
            <ControlOption value="CANCELLED">CANCELLED (Dibatalkan)</ControlOption>
          </ControlSelect>
        </FormBlock>
      </form>
    </VmsDialog>
  );
};
