import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type PlanDocument = components["schemas"]["PlanDocumentOut"];
export type Signature = components["schemas"]["SignatureOut"];

/** GET /work-plans/{id}/documents — versi dokumen rencana kerja yang terbit. */
export async function listPlanDocuments(planId: string): Promise<PlanDocument[]> {
  return (await api.get<PlanDocument[]>(`/work-plans/${planId}/documents`)).data;
}

/** GET /documents/{id}/pdf — PDF bertanda tangan sebagai Blob. */
export async function fetchDocumentPdf(documentId: string): Promise<Blob> {
  return (await api.get<Blob>(`/documents/${documentId}/pdf`, { responseType: "blob" })).data;
}

/** GET /documents/{id}/signatures — tanda tangan pada satu dokumen. */
export async function listDocumentSignatures(documentId: string): Promise<Signature[]> {
  return (await api.get<Signature[]>(`/documents/${documentId}/signatures`)).data;
}

/** POST /signatures/{id}/revoke — cabut tanda tangan (alasan wajib). */
export async function revokeSignature(signatureId: string, body: components["schemas"]["RevokeRequest"]): Promise<{ message: string }> {
  return (await api.post<{ message: string }>(`/signatures/${signatureId}/revoke`, body)).data;
}
