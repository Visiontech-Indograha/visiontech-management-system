import type { ReactNode } from "react";
import { ListEntry } from "@/components/molecules/ListBlock";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { tahapJatuhTempo } from "@/lib/dokumenKendaraan";
import { formatDate } from "@/lib/format";
import type { VehicleDocument } from "@/services/vehicleDocumentService";

/** Satu baris dokumen: jenis, kendaraan, tanggal jatuh tempo, dan tahap dalam kalimat awam. */
export function DocumentRow({ doc, action }: { doc: VehicleDocument; action?: ReactNode }) {
  const tahap = tahapJatuhTempo(doc.days_left);
  return (
    <ListEntry className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
      <div className="min-w-0 flex-1">
        <TextBlock className="font-medium">{doc.doc_type_name} · {doc.number_plate}</TextBlock>
        <TextBlock className="text-xs text-mist">
          {doc.vehicle_name}{doc.doc_no ? ` · No. ${doc.doc_no}` : ""} · berlaku sampai {formatDate(doc.expired_on)}
        </TextBlock>
      </div>
      <Pill tone={tahap.tone}>{tahap.label}</Pill>
      {action}
    </ListEntry>
  );
}
