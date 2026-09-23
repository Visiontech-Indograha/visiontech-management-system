export interface DashboardSummaryResponse {
  total_employees: number;
  active_projects: number;
  expiring_documents_count: number;
  today_absences_count: number;
  vehicles_count: number;
  tools_count: number;
}

export interface ExpiringDocumentItem {
  source: "ID_CARD" | "DRIVING_CARD" | "CERTIFICATE" | "CONTRACT";
  label: string;
  employee_id: string;
  employee_name: string;
  expire_date: string;
  days_until_expiry: number;
}

export interface EmployeeStatusResponse {
  tetap_count: number;
  kontrak_count: number;
  unspecified_count: number;
  total: number;
  tetap_percentage: number;
  kontrak_percentage: number;
}

export interface DailyReportRateResponse {
  report_date: string;
  assigned_count: number;
  reported_count: number;
  rate_percentage: number;
}

export interface FieldPerformancePoint {
  month: string;
  completed_reports: number;
}

export interface RecentActivityItem {
  type: "PROGRESS_REPORT" | "LEAVE_REQUEST" | "ABSENCE";
  message: string;
  timestamp: string;
}

export interface CalendarEventItem {
  event_date: string;
  type: "WORK_PLAN" | "LEAVE" | "DOCUMENT_EXPIRY";
  title: string;
}
