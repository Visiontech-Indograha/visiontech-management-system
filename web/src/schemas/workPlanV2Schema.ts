/**
 * web/src/schemas/workPlanV2Schema.ts
 * Skema validasi Zod untuk Rencana Kerja (Work Plan) V2 terintegrasi:
 * - work_plan_weekly (Mingguan: division, team, week_number, year, dates, status)
 * - work_plan_daily (Harian: date, site_name, GPS coordinates, attendance radius, work hours)
 * - work_plan_item (Item multi-slot: title, work_type, completion link, target_qty, slot times, location, assigned technicians)
 */

import { z } from "zod";

export const planItemV2Schema = z.object({
  item_id: z.string().uuid().optional(),
  daily_plan_id: z.string().uuid().optional(),
  weekly_plan_id: z.string().uuid().optional(),
  work_type_id: z.string().uuid({ message: "Jenis pekerjaan wajib dipilih" }),
  title: z.string().min(3, { message: "Judul tugas minimal 3 karakter" }).max(255),
  completion_id: z.string().uuid().nullable().optional(),
  target_qty: z.number().min(0.01, { message: "Target unit harus lebih besar dari 0" }),
  completed_qty: z.number().min(0),
  progress_percent: z.number().min(0).max(100),
  start_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, { message: "Format jam mulai tidak valid (HH:MM)" }).optional().or(z.literal("")),
  end_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, { message: "Format jam selesai tidak valid (HH:MM)" }).optional().or(z.literal("")),
  location_name: z.string().max(255).optional().or(z.literal("")),
  site_lat: z.number().min(-90).max(90).optional().nullable(),
  site_lng: z.number().min(-180).max(180).optional().nullable(),
  assigned_employee_ids: z.array(z.string().uuid()),
  status: z.enum(["PENDING", "IN_PROGRESS", "COMPLETED", "DELAYED", "CANCELLED", "DONE", "SHIFTED_DAY", "SHIFTED_WEEK"]),
  rollover_approval_status: z.enum(["NONE", "WAITING_PM", "APPROVED_BY_PM", "REJECTED_BY_PM"]),
  delay_reason: z.string().optional().nullable(),
});

export type PlanItemV2Value = z.infer<typeof planItemV2Schema>;

export const dailyPlanV2Schema = z.object({
  daily_plan_id: z.string().uuid().optional(),
  weekly_plan_id: z.string().uuid().optional(),
  work_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, { message: "Format tanggal harus YYYY-MM-DD" }),
  site_name: z.string().min(2, { message: "Nama site/lokasi kerja wajib diisi" }).max(255),
  site_lat: z.number().min(-90).max(90, { message: "Latitude harus antara -90 dan 90" }),
  site_lng: z.number().min(-180).max(180, { message: "Longitude harus antara -180 dan 180" }),
  attendance_radius_m: z.number().min(10, { message: "Radius absensi minimal 10 meter" }),
  clock_in_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, { message: "Format jam masuk tidak valid (HH:MM)" }),
  clock_out_time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, { message: "Format jam pulang tidak valid (HH:MM)" }),
  status: z.enum(["SCHEDULED", "ONGOING", "PARTIAL", "COMPLETED", "HOLIDAY", "CANCELLED"]),
  is_holiday: z.boolean(),
  items: z.array(planItemV2Schema),
});

export type DailyPlanV2Value = z.infer<typeof dailyPlanV2Schema>;

export const weeklyPlanV2Schema = z.object({
  weekly_plan_id: z.string().uuid().optional(),
  division_id: z.string().uuid({ message: "Divisi kerja wajib dipilih" }),
  team_id: z.string().uuid({ message: "Tim kerja wajib dipilih" }),
  week_number: z.number().int().min(1).max(53, { message: "Minggu harus antara 1 sampai 53" }),
  year: z.number().int().min(2020).max(2100, { message: "Tahun tidak valid" }),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, { message: "Tanggal mulai harus YYYY-MM-DD" }),
  end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, { message: "Tanggal selesai harus YYYY-MM-DD" }),
  status: z.enum(["DRAFT", "SUBMITTED", "APPROVED", "ONGOING", "COMPLETED", "REJECTED"]),
  tool_ids: z.array(z.string().uuid()),
  vehicle_id: z.string().uuid().optional().or(z.literal("")),
  driver_employee_id: z.string().uuid().optional().or(z.literal("")),
  days: z.array(dailyPlanV2Schema).min(1, { message: "Rencana kerja harus memiliki minimal 1 hari kerja" }),
}).refine((data) => data.end_date >= data.start_date, {
  message: "Tanggal selesai tidak boleh lebih awal dari tanggal mulai",
  path: ["end_date"],
});

export type WeeklyPlanV2Value = z.infer<typeof weeklyPlanV2Schema>;
