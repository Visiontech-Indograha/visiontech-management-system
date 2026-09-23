export interface LocationPoint {
  longitude: number;
  latitude: number;
}

export interface AbsenceResponse {
  id: string;
  employee_id: string;
  check_in_time: string;
  check_in_location: LocationPoint;
  check_out_time: string | null;
  check_out_location: LocationPoint | null;
  photo_url: string | null;
  status: "PRESENT" | "LATE" | "ABSENT" | "LEAVE";
  sync_version: number;
  sync_status: string;
}

export type LeaveType = "ANNUAL" | "SICK" | "MATERNITY" | "UNPAID" | "OFF_DAY" | "ADD_OFF_DAY";

export interface LeaveRequestResponse {
  id: string;
  employee_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  reason: string | null;
  attachment_url: string | null;
  approval_status: "PENDING" | "APPROVED_PM" | "APPROVED_OM" | "REJECTED";
  pm_approver_id: string | null;
  om_approver_id: string | null;
  sync_version: number;
  sync_status: string;
}

export interface LeaveCountResponse {
  id: string;
  employee_id: string;
  year: number;
  total_leave: number;
  used_leave: number;
  offday_total: number;
  offday_used: number;
  annual_remaining: number;
  offday_remaining: number;
}
