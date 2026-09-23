export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "RETURNED";
export type SyncStatus = "PENDING" | "SYNCED" | "CONFLICT";

export interface VehicleBookingLogResponse {
  id: string;
  vehicle_id: string;
  employee_id: string;
  purpose: string;
  start_time: string;
  end_time: string | null;
  odometer_start: number;
  odometer_end: number | null;
  notes: string | null;
  approval_status: ApprovalStatus;
  approved_by_id: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
}

export interface LogbookToolResponse {
  id: string;
  item_id: string;
  employee_id: string;
  borrow_date: string;
  return_date: string | null;
  quantity: number;
  condition_borrow: string;
  condition_return: string | null;
  approval_status: ApprovalStatus;
  approved_by_id: string | null;
  sync_version: number;
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
}

export interface VehicleServiceResponse {
  id: string;
  vehicle_id: string;
  service_date: string;
  description: string;
  cost: number;
  mechanic_name: string;
  receipt_url: string | null;
}
