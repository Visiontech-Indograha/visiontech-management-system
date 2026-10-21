import type { ReactNode } from "react";
import { formatDate } from "@/lib/format";
import type { Employee } from "@/services/employeeService";
import { EmployeeStatusPill } from "./EmployeeStatusPill";
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

/** Data pokok karyawan V2; email hanya bila `canSeePrivate`. */
export function EmployeeProfileCard({ employee: e, canSeePrivate }: {
  employee: Employee;
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
          <Row label="Jabatan">{e.position_name}</Row>
          <Row label="Divisi">{e.division_name}</Row>
          <Row label="Kantor">{e.office_name}</Row>
          <Row label="Status"><EmployeeStatusPill status={e.offboarding_status} /></Row>
          <Row label="Tanggal bergabung">{formatDate(e.join_date)}</Row>
          <Row label="Akhir PKWT">{e.pkwt_end_date ? formatDate(e.pkwt_end_date) : "Karyawan tetap"}</Row>
          <Row label="Wajah">{e.face_enrolled ? <Pill tone="success">Terdaftar</Pill> : <Pill>Belum</Pill>}</Row>
          {canSeePrivate && <Row label="Email">{e.email}</Row>}
        </ListBlock>
        {!canSeePrivate && (
          <TextBlock className="border-t border-line py-3 text-caption text-mist">
            Email, alamat, dan dokumen identitas hanya terlihat oleh pemilik serta HR.
          </TextBlock>
        )}
      </div>
  );
}
