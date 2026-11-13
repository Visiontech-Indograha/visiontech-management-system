export type DocTone = "danger" | "warning" | "info";

/** Tahap jatuh tempo dalam kalimat awam dari sisa hari (negatif = sudah lewat). */
export function tahapJatuhTempo(daysLeft: number): { label: string; tone: DocTone } {
  if (daysLeft < 0) return { label: `Sudah lewat ${-daysLeft} hari`, tone: "danger" };
  if (daysLeft === 0) return { label: "Jatuh tempo hari ini", tone: "danger" };
  const label = `Jatuh tempo ${daysLeft} hari lagi`;
  if (daysLeft <= 7) return { label, tone: "danger" };
  if (daysLeft <= 30) return { label, tone: "warning" };
  return { label, tone: "info" };
}
