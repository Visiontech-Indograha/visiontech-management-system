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
  origin_item_id?: string | null;
  shifted_to_daily_id?: string | null;
  allocated_to_weekly_id?: string | null;
  delay_reason?: string | null;
  rollover_approval_status?: string | null;
  completion_id?: string | null;
  task_phase?: "SURVEY" | "PREPARATION" | "MAIN_INSTALLATION" | "TESTING_COMMISSIONING" | "FINISHING" | string | null;
  is_main_deliverable?: boolean;
  depends_on_item_id?: string | null;
  realization_photos_json?: string[] | null;
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

export interface TaskChainItemDetail {
  item_id: string;
  weekly_plan_id?: string | null;
  daily_plan_id?: string | null;
  work_date?: string | null;
  title: string;
  task_phase?: string | null;
  is_main_deliverable?: boolean;
  target_qty: number;
  completed_qty: number;
  progress_percent: number;
  status: string;
  completion_id?: string | null;
  create_at?: string | null;
}

export interface TaskChainStatusOut {
  root_item_id: string;
  initial_total_target: number;
  total_completed_across_weeks: number;
  total_progress_percent: number;
  is_eligible_for_completion: boolean;
  status_label: string;
  existing_completion_id?: string | null;
  all_linked_item_ids: string[];
  items: TaskChainItemDetail[];
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

/** PM Keputusan Rollover: menyetujui (ke tanggal baru / jadwal lain) atau menolak. */
export async function pmApproveOrMoveItem(itemId: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await api.post<Record<string, unknown>>(`/work-plans/items/${itemId}/rollover-decision`, body);
  return res.data;
}

/** Mengambil rantai rollover (task chain) lintas hari/minggu. */
export async function getTaskChainStatus(itemId: string): Promise<Record<string, unknown>[]> {
  const res = await api.get<Record<string, unknown>[]>(`/work-plans/items/${itemId}/chain`);
  return res.data;
}

/** Mengambil rincian jadwal multi-slot harian beserta SOP dan order klien. */
export async function getDailyScheduleDetail(dailyPlanId: string): Promise<DailyScheduleDetail> {
  const res = await api.get<DailyScheduleDetail>(`/work-plans/daily/${dailyPlanId}`);
  return res.data;
}
