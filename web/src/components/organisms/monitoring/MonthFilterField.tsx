import { TextField } from "@/components/molecules/Field";

/** Saring per bulan (`YYYY-MM`); kosong = semua bulan. */
export function MonthFilterField({ value, onChange, hint }: { value: string; onChange: (month: string) => void; hint?: string }) {
  return <TextField label="Bulan" type="month" value={value} onChange={(e) => onChange(e.target.value)} hint={hint} />;
}
