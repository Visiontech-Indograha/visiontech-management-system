export enum DocumentType {
  HES_PLAN = "HES_PLAN",
  SOP = "SOP",
  POLICY = "POLICY",
  OTHER = "OTHER",
}

export interface InternalDocument {
  id: string;
  document_type: DocumentType;
  title: string;
  description?: string | null;
  upload_date: string;
  file_url?: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export type InternalDocumentCreate = Omit<InternalDocument, "id" | "uploaded_by" | "created_at" | "updated_at">;

export interface OutpostLetter {
  id: string;
  letter_number: string;
  subject: string;
  issue_date: string;
  employee_id: string;
  file_url?: string | null;
  created_at: string;
  updated_at: string;
}

export type OutpostLetterCreate = Omit<OutpostLetter, "id" | "created_at" | "updated_at">;
