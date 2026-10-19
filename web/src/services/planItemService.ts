/**
 * web/src/services/planItemService.ts
 * Layanan komunikasi API untuk item penugasan rencana kerja, deteksi tabrakan waktu,
 * pembaruan capaian progres, dan fungsi PM Full Override.
 */

import { api } from "@/lib/apiClient";

export interface ConflictDetail {
  conflict_type: "EMPLOYEE" | "VEHICLE";
  entity_id: string;
  entity_name: string;
  conflicting_item_id: string;
  conflicting_title: string;
  start_time?: string | null;
  end_time?: string | null;
}

export interface CheckConflictIn {
  work_date: string;
  start_time: string;
  end_time: string;
  employee_ids?: string[];
  vehicle_id?: string | null;
  exclude_item_id?: string | null;
}

export interface CheckConflictOut {
  has_conflict: boolean;
  conflicts: ConflictDetail[];
}

export interface UpdateItemProgressIn {
  completed_qty?: number | null;
  progress_percent?: number | null;
  status?: string | null;
  delay_reason?: string | null;
}

export interface UpdateItemProgressOut {
  item_id: string;
  completed_qty: number;
  progress_percent: number;
  status: string;
  delay_reason?: string | null;
}

export interface RequestRolloverIn {
  delay_reason: string;
  target_daily_plan_id?: string | null;
}

export interface RequestRolloverOut {
  item_id: string;
  status: string;
  rollover_approval_status: string;
  delay_reason: string;
  shifted_to_daily_id?: string | null;
}

export interface PmApproveOrMoveIn {
  action: "APPROVED" | "REJECTED" | "MOVE_SLOT";
  pm_override_reason: string;
  target_daily_plan_id?: string | null;
  target_weekly_plan_id?: string | null;
  target_start_time?: string | null;
  target_end_time?: string | null;
  new_status?: string | null;
}

export interface PmApproveOrMoveOut {
  success: boolean;
  action: string;
  item_id: string;
  new_item_id?: string | null;
  status: string;
  rollover_approval_status: string;
  message: string;
}

export interface SopImageRequirement {
  title: string;
  description?: string | null;
  path_image?: string | null;
}

export interface ItemScheduleSlot {
  item_id: string;
  start_time?: string | null;
  end_time?: string | null;
  title: string;
  location_name?: string | null;
  site_lat?: number | null;
  site_lng?: number | null;
  target_qty: number;
  completed_qty: number;
  progress_percent: number;
  status: string;
  assigned_employee_ids?: string[];
  work_type?: {
    work_type_id: string;
    name: string;
    description?: string | null;
    sop_image_requirements?: SopImageRequirement[];
  } | null;
  work_completion_order?: {
    completion_id: string;
    order_number: string;
    client_name: string;
    project_title: string;
    total_target_unit?: number | null;
    unit_measure?: string | null;
    order_status: string;
    priority_level?: string | null;
  } | null;
}

export interface DailyScheduleDetail {
  daily_plan_id: string;
  work_date: string;
  status: string;
  can_pm_edit: boolean;
  preview_pdf_url?: string | null;
  weekly_context: {
    weekly_plan_id: string;
    week_number: number;
    year: number;
    division: { division_id: string; name: string };
    team: { team_id: string; name: string };
  };
  default_attendance_site: {
    site_name?: string | null;
    site_lat?: number | null;
    site_lng?: number | null;
    attendance_radius_m?: number | null;
    clock_in_time?: string | null;
    clock_out_time?: string | null;
  };
  items_schedule_slots: ItemScheduleSlot[];
}

/** Memeriksa tabrakan jadwal teknisi atau kendaraan. */
export async function checkScheduleConflict(body: CheckConflictIn): Promise<CheckConflictOut> {
  const res = await api.post<CheckConflictOut>("/work-plans/items/check-schedule-conflict", body);
  return res.data;
}

/** Memperbarui capaian aktual dan persentase progres tugas. */
export async function updateItemProgress(itemId: string, body: UpdateItemProgressIn): Promise<UpdateItemProgressOut> {
  const res = await api.patch<UpdateItemProgressOut>(`/work-plans/items/${itemId}/progress`, body);
  return res.data;
}

/** Mengajukan rollover tugas terkendala ke hari berikutnya. */
export async function requestItemRollover(itemId: string, body: RequestRolloverIn): Promise<RequestRolloverOut> {
  const res = await api.post<RequestRolloverOut>(`/work-plans/items/${itemId}/request-rollover`, body);
  return res.data;
}

/** PM Full Override: menyetujui, menolak, atau memindahkan tugas secara paksa. */
export async function pmApproveOrMoveItem(itemId: string, body: PmApproveOrMoveIn): Promise<PmApproveOrMoveOut> {
  const res = await api.post<PmApproveOrMoveOut>(`/work-plans/items/${itemId}/pm-approve-or-move`, body);
  return res.data;
}

/** Mengambil rincian jadwal multi-slot harian beserta SOP dan order klien. */
export async function getDailyScheduleDetail(dailyPlanId: string): Promise<DailyScheduleDetail> {
  const res = await api.get<DailyScheduleDetail>(`/work-plans/daily/${dailyPlanId}`);
  return res.data;
}
