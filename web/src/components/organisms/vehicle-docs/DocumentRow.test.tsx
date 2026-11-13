import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { VehicleDocument } from "@/services/vehicleDocumentService";
import { DocumentRow } from "./DocumentRow";

const doc = (days_left: number): VehicleDocument => ({
  vehicle_document_id: "d1", vehicle_id: "v1", vehicle_name: "Hilux", number_plate: "BM 1234 XY", office_id: "o1",
  doc_type_code: "STNK", doc_type_name: "STNK", doc_no: null, issued_on: null, expired_on: "2026-12-01",
  file_id: null, status: "active", catatan: null, days_left, created_at: "2026-01-01T00:00:00Z",
});

describe("DocumentRow", () => {
  it("menampilkan tahap jatuh tempo dalam kalimat awam", () => {
    const { rerender } = render(<ul><DocumentRow doc={doc(12)} /></ul>);
    expect(screen.getByText("Jatuh tempo 12 hari lagi")).toBeTruthy();
    rerender(<ul><DocumentRow doc={doc(-3)} /></ul>);
    expect(screen.getByText("Sudah lewat 3 hari")).toBeTruthy();
  });
});
