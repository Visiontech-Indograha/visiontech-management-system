import { lazy } from "react";

/** Halaman dimuat saat dibuka (code-splitting) — muatan awal kecil (R-12, performa). */
export const AssetsPage = lazy(() => import("@/features/assets/AssetsPage").then((m) => ({ default: m.AssetsPage })));
export const AttendancePage = lazy(() => import("@/features/attendance/AttendancePage").then((m) => ({ default: m.AttendancePage })));
export const AuditLogPage = lazy(() => import("@/features/audit/AuditLogPage").then((m) => ({ default: m.AuditLogPage })));
export const DirectoryPage = lazy(() => import("@/features/directory/DirectoryPage").then((m) => ({ default: m.DirectoryPage })));
export const EmployeeDetailPage = lazy(() => import("@/features/directory/EmployeeDetailPage").then((m) => ({ default: m.EmployeeDetailPage })));
export const MyDocumentsPage = lazy(() => import("@/features/directory/MyDocuments").then((m) => ({ default: m.MyDocumentsPage })));
export const WorkTypesPage = lazy(() => import("@/features/work-types/WorkTypesPage").then((m) => ({ default: m.WorkTypesPage })));
export const SitesPage = lazy(() => import("@/features/sites/SitesPage").then((m) => ({ default: m.SitesPage })));
export const WorkPlanDetailPage = lazy(() => import("@/features/work-plans/WorkPlanDetailPage").then((m) => ({ default: m.WorkPlanDetailPage })));
export const PlanEditorPage = lazy(() => import("@/features/work-plans/PlanEditorPage").then((m) => ({ default: m.PlanEditorPage })));
export const WorkPlansPage = lazy(() => import("@/features/work-plans/WorkPlansPage").then((m) => ({ default: m.WorkPlansPage })));
export const AttendanceRecapPage = lazy(() => import("@/features/monitoring/AttendanceRecapPage").then((m) => ({ default: m.AttendanceRecapPage })));
export const OvertimeRecapPage = lazy(() => import("@/features/monitoring/OvertimeRecapPage").then((m) => ({ default: m.OvertimeRecapPage })));
export const TimelinePage = lazy(() => import("@/features/monitoring/TimelinePage").then((m) => ({ default: m.TimelinePage })));
export const AccountPage = lazy(() => import("@/features/account/AccountPage").then((m) => ({ default: m.AccountPage })));
export const PresentationPage = lazy(() => import("@/features/work-plans/PresentationPage").then((m) => ({ default: m.PresentationPage })));
