import type { ReactNode } from "react";
import { formatDate } from "@/lib/format";
import { ATTENDANCE_MODE_LABEL } from "@/lib/attendanceModeLabels";
import type { Employee } from "@/services/employeeService";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock } from "@/components/molecules/ListBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { useFileUrl } from "@/hooks/useFileUrl";

const Row = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="flex justify-between gap-4 border-b border-line py-2 last:border-0">
    <TextBlock as="dt" className="text-mist">{label}</TextBlock>
    <TextBlock as="dd" className="text-right font-medium">{children ?? "-"}</TextBlock>
  </div>
);

/** Data pokok karyawan; kontak pribadi hanya bila `canSeePrivate` (M2-01 — server pun menyaringnya). */
export function EmployeeProfileCard({ employee: e, unitName, canSeePrivate }: {
  employee: Employee;
  unitName: string | null;
  canSeePrivate: boolean;
}) {
  // Presigned URL: <img src> tidak bisa mengirim header Authorization.
  const { data: photoUrl } = useFileUrl(e.photo_file_id, "view");

  return (
      <div className="mb-8 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-2">
        {photoUrl && (
          <div className="mb-4 flex justify-center">
            <ImageView
              src={photoUrl}
              alt={e.full_name}
              className="h-24 w-24 rounded-full object-cover"
            />
          </div>
        )}
        <ListBlock as="dl" className="text-sm">
          <Row label="No. karyawan">{e.employee_no}</Row>
          <Row label="Jabatan">{e.position}</Row>
          <Row label="Unit">{unitName}</Row>
          <Row label="Akun">{e.is_active ? <Pill tone="success">Aktif</Pill> : <Pill>Nonaktif</Pill>}</Row>
          <Row label="Tanggal bergabung">{formatDate(e.join_date)}</Row>
          <Row label="Absen lewat">{ATTENDANCE_MODE_LABEL[e.attendance_mode ?? "FIELD"]}</Row>
          {canSeePrivate && (
            <>
              <Row label="Email">{e.email}</Row>
              <Row label="No. telepon">{e.phone}</Row>
              <Row label="Tanggal lahir">{e.birth_date ? formatDate(e.birth_date) : null}</Row>
              <Row label="Alamat">{e.address}</Row>
            </>
          )}
          {e.offboarded_at && (
            <Row label="Keluar">
              {formatDate(e.offboarded_at)} – {e.offboarding_reason ?? "-"}
            </Row>
          )}
        </ListBlock>
        {!canSeePrivate && (
          <TextBlock className="border-t border-line py-3 text-caption text-mist">
            Data kontak pribadi dan dokumen identitas hanya terlihat oleh pemilik serta HR.
          </TextBlock>
        )}
      </div>
  );
}
