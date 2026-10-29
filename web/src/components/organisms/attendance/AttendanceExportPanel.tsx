import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { errorMessage } from "@/lib/errors";
import { exportAttendanceCsv } from "@/services/attendanceService";

/** YYYY-MM-DD menurut waktu lokal browser. */
const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/**
 * Ekspor CSV absensi (GET /attendance/export). Hanya dirender untuk peran ber-izin export:attendance (Finance).
 * Rentang tanggal wajib dan "Dari" tidak boleh setelah "Sampai" (sama dengan aturan server).
 */
export function AttendanceExportPanel() {
  const today = new Date();
  const [from, setFrom] = useState(isoDay(new Date(today.getFullYear(), today.getMonth(), 1)));
  const [to, setTo] = useState(isoDay(today));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!from || !to) return setError("Isi tanggal mulai dan tanggal akhir.");
    if (from > to) return setError("Tanggal mulai tidak boleh setelah tanggal akhir.");
    setError(null);
    setBusy(true);
    try {
      await exportAttendanceCsv(from, to);
      toast.success("Ekspor CSV absensi diunduh.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormBlock onSubmit={submit} aria-label="Ekspor CSV absensi" className="mb-4 grid items-end gap-x-3 md:grid-cols-4">
      <TextField label="Ekspor dari" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
      <TextField label="Ekspor sampai" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      <div className="mb-4">
        <ActionButton type="submit" variant="outline" disabled={busy}>
          {busy ? "Mengunduh…" : "Ekspor CSV"}
        </ActionButton>
      </div>
      <FormErrorText message={error} className="mb-4 md:col-span-4" />
    </FormBlock>
  );
}
