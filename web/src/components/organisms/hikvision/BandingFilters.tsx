import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ListToolbar } from "@/components/organisms/ListToolbar";
import { STATUS_BANDING, STATUS_LABEL } from "@/lib/hikvisionBanding";
import type { Perangkat } from "@/services/hikvisionService";

export interface BandingFilterValue {
  deviceId: string;
  dari: string;
  sampai: string;
  status: string;
  input: string;
}

/** Filter pembanding: mesin, rentang tanggal (maks 31 hari), status, dan cari awalan nama. */
export function BandingFilters({ devices, value, onChange, onReset, active }: {
  devices: Perangkat[];
  value: BandingFilterValue;
  onChange: (patch: Partial<BandingFilterValue>) => void;
  onReset: () => void;
  active: boolean;
}) {
  return (
    <div>
      <div className="grid gap-x-3 md:grid-cols-4">
        <SelectField label="Mesin" value={value.deviceId} onChange={(e) => onChange({ deviceId: e.target.value })}>
          {devices.map((d) => (
            <ControlOption key={d.device_id} value={d.device_id}>{`${d.name} (${d.office_name})`}</ControlOption>
          ))}
        </SelectField>
        <TextField label="Dari tanggal" type="date" value={value.dari} max={value.sampai || undefined} onChange={(e) => onChange({ dari: e.target.value })} />
        <TextField label="Sampai tanggal" type="date" value={value.sampai} min={value.dari || undefined} onChange={(e) => onChange({ sampai: e.target.value })} />
        <SelectField label="Status" value={value.status} onChange={(e) => onChange({ status: e.target.value })}>
          <ControlOption value="">Semua status</ControlOption>
          {STATUS_BANDING.map((s) => (
            <ControlOption key={s} value={s}>{STATUS_LABEL[s]}</ControlOption>
          ))}
        </SelectField>
      </div>
      <ListToolbar value={value.input} onChange={(v) => onChange({ input: v })} placeholder="Cari dari awal nama karyawan" active={active} onReset={onReset} />
    </div>
  );
}
