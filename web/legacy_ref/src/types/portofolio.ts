export interface CompanyExperience {
  id: string;
  project_name: string;
  client_name: string;
  category_ce_id: string;
  start_date: string;
  end_date?: string | null;
  description?: string | null;
  document_url?: string | null;
  created_at: string;
  updated_at: string;
}

export type CompanyExperienceCreate = Omit<CompanyExperience, "id" | "created_at" | "updated_at">;

export interface CategoryCE {
  id: string;
  name: string;
  description?: string | null;
}
