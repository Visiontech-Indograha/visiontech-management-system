import { TextField } from "@/components/molecules/Field";

/** Rentang tanggal "Dari" – "Sampai" (`YYYY-MM-DD`); kosong = tanpa batas. */
export function DateRangeFilter({ from, to, onFromChange, onToChange }: {
  from: string;
  to: string;
  onFromChange: (date: string) => void;
  onToChange: (date: string) => void;
}) {
  return (
    <div className="grid gap-x-3 md:max-w-md md:grid-cols-2">
      <TextField label="Dari tanggal" type="date" value={from} onChange={(e) => onFromChange(e.target.value)} />
      <TextField label="Sampai tanggal" type="date" value={to} onChange={(e) => onToChange(e.target.value)} />
    </div>
  );
}
