export type WorkPlanStatus = "DRAFT" | "ACTIVE" | "COMPLETED" | "CANCELLED";
export type ReportType =
  | "PEMASANGAN_BARU"
  | "PERGANTIAN_DEVICE"
  | "PREVENTIVE_MAINTENANCE"
  | "REPORT_SURVEY";
export type SyncStatus = "PENDING" | "SYNCED" | "CONFLICT";

export interface BillOfMaterialResponse {
  id: string;
  progress_report_id: string;
  material_name: string;
  quantity: number;
  unit: string | null;
  brand: string | null;
  notes: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
}

export interface ProgressReportDetailResponse {
  id: string;
  progress_report_id: string;
  item_description: string;
  quantity: number;
  unit: string | null;
  notes: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
}

export interface ProgressReportResponse {
  id: string;
  work_plan_id: string;
  employee_id: string;
  report_type: ReportType;
  extra_metadata: Record<string, unknown> | null;
  notes: string | null;
  attachment_url: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
  details: ProgressReportDetailResponse[];
  bill_of_materials: BillOfMaterialResponse[];
}

export interface WorkPlanMemberResponse {
  id: string;
  employee_id: string;
  role_in_team: string | null;
}

export interface WorkPlanResponse {
  id: string;
  title: string;
  description: string | null;
  status: WorkPlanStatus;
  planned_date: string | null;
  actual_date: string | null;
  created_by_id: string | null;
  assignee_id: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
  progress_reports: ProgressReportResponse[];
  members: WorkPlanMemberResponse[];
}
