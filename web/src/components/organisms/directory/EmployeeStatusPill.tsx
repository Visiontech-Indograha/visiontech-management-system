import { Pill } from "@/components/molecules/Pill";

const LABEL: Record<string, string> = { active: "Aktif", in_process: "Proses keluar", offboarded: "Selesai bekerja" };

/** Status kerja karyawan V2 (`offboarding_status`). */
export function EmployeeStatusPill({ status }: { status: string }) {
  return <Pill tone={status === "active" ? "success" : undefined}>{LABEL[status] ?? status}</Pill>;
}
